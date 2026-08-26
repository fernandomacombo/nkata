import hashlib
from io import BytesIO
import random
from urllib.parse import urlparse

import qrcode
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response

from .access_api import _validar_imagem
from .identity_models import VerificacaoIdentidadeNKATA
from .identity_verification_service import (
    CAPTURE_LABELS,
    CAPTURE_ORDER,
    finalize_identity_analysis,
    inspect_identity_capture,
    next_capture,
)
from .media_validation import sanitized_image_upload
from .throttles import (
    IdentityCaptureRateThrottle,
    IdentitySessionRateThrottle,
    IdentityStatusRateThrottle,
)


SELFIE_CHALLENGES = (
    "Sorria ligeiramente e mantenha os olhos na câmara.",
    "Aproxime um pouco o rosto e olhe para a câmara.",
    "Levante um pouco o queixo e olhe para a câmara.",
)


def identity_email_hash(email):
    normalized = str(email or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _expire_if_needed(session):
    if session.expirada and session.status not in {"APROVADA", "REJEITADA", "EXPIRADA"}:
        session.status = "EXPIRADA"
        session.save(update_fields=["status", "atualizado_em"])
    return session.status == "EXPIRADA"


def serialize_identity_session(session):
    expired = _expire_if_needed(session)
    current = next_capture(session) if not session.capturas_completas else "concluida"
    checks = session.verificacoes_imagem or {}
    completed = [field for field in CAPTURE_ORDER if bool(getattr(session, field))]
    return {
        "token": str(session.token),
        "status": session.status,
        "status_label": session.get_status_display(),
        "risk": session.risco,
        "current_capture": current,
        "current_label": CAPTURE_LABELS.get(current, "Concluída"),
        "completed_captures": completed,
        "checks": {
            field: {
                "score": data.get("score"),
                "checks": data.get("checks", {}),
            }
            for field, data in checks.items()
        },
        "selfie_challenge": session.desafio_selfie,
        "capture_complete": session.capturas_completas,
        "can_submit": session.pode_anexar_ao_pedido and not expired,
        "automatically_approved": session.status == "APROVADA",
        "face_match_score": (
            float(session.correspondencia_facial)
            if session.correspondencia_facial is not None
            else None
        ),
        "liveness_confirmed": session.vivacidade_confirmada,
        "expires_at": session.expira_em,
        "expired": expired,
    }


def _capture_url(request, token):
    configured = getattr(settings, "NKATA_PUBLIC_APP_URL", "")
    requested_origin = str(request.GET.get("app_origin", "")).strip().rstrip("/")
    request_origin = f"{request.scheme}://{request.get_host()}"
    base = configured or request_origin
    if requested_origin:
        parsed = urlparse(requested_origin)
        request_host = request.get_host().split(":", 1)[0].lower()
        if parsed.scheme in {"http", "https"} and parsed.hostname == request_host:
            base = requested_origin
    return f"{base}/verificar-identidade/{token}/"


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([IdentitySessionRateThrottle])
def api_criar_sessao_nkata_id(request):
    email = str(request.data.get("email", "")).strip().lower()
    try:
        idade = int(request.data.get("idade", 0))
    except (TypeError, ValueError):
        idade = 0
    aceita_biometria = request.data.get("aceita_biometria") in {True, "true", "on", "1", 1}

    errors = {}
    if not email or "@" not in email:
        errors["email"] = ["Informe um email válido."]
    if idade < 18:
        errors["idade"] = ["O NKATA é apenas para pessoas com 18 anos ou mais."]
    if not aceita_biometria:
        errors["aceita_biometria"] = [
            "É necessário autorizar a verificação do documento e do rosto."
        ]
    if errors:
        return Response({"detail": "Revise os dados do NKATA ID.", "errors": errors}, status=400)

    session = VerificacaoIdentidadeNKATA.objects.create(
        email_hash=identity_email_hash(email),
        idade_declarada=idade,
        aceita_biometria=True,
        desafio_selfie=random.choice(SELFIE_CHALLENGES),
    )
    return Response(serialize_identity_session(session), status=201)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([IdentityStatusRateThrottle])
def api_estado_nkata_id(request, token):
    session = VerificacaoIdentidadeNKATA.objects.filter(token=token).first()
    if not session:
        return Response({"detail": "Sessão NKATA ID não encontrada."}, status=404)
    return Response(serialize_identity_session(session))


@api_view(["GET"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([IdentityStatusRateThrottle])
def api_qr_nkata_id(request, token):
    session = VerificacaoIdentidadeNKATA.objects.filter(token=token).first()
    if not session or _expire_if_needed(session):
        return Response({"detail": "Sessão NKATA ID não encontrada."}, status=404)
    qr = qrcode.QRCode(version=None, box_size=8, border=3)
    qr.add_data(_capture_url(request, token))
    qr.make(fit=True)
    image = qr.make_image(fill_color="#241f1d", back_color="#ffffff")
    output = BytesIO()
    image.save(output, format="PNG")
    response = HttpResponse(output.getvalue(), content_type="image/png")
    response["Cache-Control"] = "private, max-age=60"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([IdentityCaptureRateThrottle])
def api_capturar_nkata_id(request, token, capture_type):
    if capture_type not in CAPTURE_ORDER:
        return Response({"detail": "Tipo de captura inválido."}, status=404)
    session = VerificacaoIdentidadeNKATA.objects.filter(token=token).first()
    if not session:
        return Response({"detail": "Sessão NKATA ID não encontrada."}, status=404)
    if _expire_if_needed(session):
        return Response({"detail": "Esta sessão expirou. Inicie uma nova verificação."}, status=410)
    bound_session_can_recapture = bool(
        session.pedido_id and session.status in {"REPETIR", "EM_CAPTURA"}
    )
    if session.status in {"APROVADA", "REJEITADA"} or (
        session.pedido_id and not bound_session_can_recapture
    ):
        return Response({"detail": "Esta verificação já foi concluída."}, status=409)

    upload = request.FILES.get("imagem")
    error = _validar_imagem(upload)
    if error:
        return Response({"detail": error}, status=400)
    try:
        safe_upload = sanitized_image_upload(upload)
        result = inspect_identity_capture(safe_upload, capture_type)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return Response({"detail": "Não foi possível analisar esta imagem."}, status=400)

    if not result["accepted"]:
        return Response({
            "detail": "A imagem ainda não tem qualidade suficiente.",
            "capture": capture_type,
            "quality": result,
        }, status=422)

    previous = getattr(session, capture_type)
    if previous:
        previous.delete(save=False)
    safe_upload.seek(0)
    getattr(session, capture_type).save(safe_upload.name, safe_upload, save=False)
    image_checks = dict(session.verificacoes_imagem or {})
    image_checks[capture_type] = result
    session.verificacoes_imagem = image_checks
    session.status = "EM_CAPTURA"
    session.etapa_atual = next_capture(session)
    if request.data.get("usar_foto_verificada") in {True, "true", "on", "1", 1}:
        session.usar_foto_verificada = True
    session.save()

    if session.capturas_completas:
        finalize_identity_analysis(session)
    return Response(serialize_identity_session(session))
