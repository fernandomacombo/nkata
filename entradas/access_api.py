import hashlib
import os
import uuid

from PIL import Image, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import permissions
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response

from .forms import PedidoEntradaForm
from .access_email_notifications import send_access_receipt_email
from .identity_models import VerificacaoIdentidadeNKATA
from .media_validation import image_dimensions_are_safe, sanitized_image_upload
from .models import PedidoEntrada, PerfilNKATA
from .throttles import (
    AccessCodeRecoveryRateThrottle,
    AccessRequestRateThrottle,
    AccessStatusRateThrottle,
)


MAX_ACCESS_IMAGE_SIZE = 6 * 1024 * 1024
ALLOWED_ACCESS_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
PROFILE_IMAGE_FIELDS = [
    "foto_perfil",
    "foto_extra_1",
    "foto_extra_2",
    "foto_extra_3",
]
LEGACY_IDENTITY_IMAGE_FIELDS = [
    "bi_frente",
    "bi_verso",
    "selfie_com_bi",
]
IMAGE_FIELDS = PROFILE_IMAGE_FIELDS + LEGACY_IDENTITY_IMAGE_FIELDS

STATUS_CONTENT = {
    "PENDENTE": {
        "title": "O seu pedido foi recebido.",
        "message": "Os dados chegaram em segurança. A equipa ainda vai iniciar a análise.",
        "tone": "waiting",
        "stage": 1,
    },
    "EM_ANALISE": {
        "title": "A análise está em andamento.",
        "message": "A equipa está a confirmar os dados, fotografias e documentos enviados.",
        "tone": "review",
        "stage": 2,
    },
    "PRECISA_CORRIGIR": {
        "title": "Precisamos de uma correção.",
        "message": (
            "Há informação que precisa ser atualizada. A equipa entrará em contacto "
            "pelo email usado no pedido com as orientações necessárias."
        ),
        "tone": "attention",
        "stage": 3,
    },
    "APROVADO": {
        "title": "O seu pedido foi aprovado.",
        "message": (
            "A entrada foi aprovada. Falta concluir o questionário e criar a sua "
            "palavra-passe através do link privado fornecido pela equipa NKATA."
        ),
        "tone": "success",
        "stage": 4,
    },
    "RECUSADO": {
        "title": "O pedido não foi aprovado.",
        "message": "A análise foi concluída e o pedido não pôde ser aprovado neste momento.",
        "tone": "closed",
        "stage": 3,
    },
    "BLOQUEADO": {
        "title": "O pedido está indisponível.",
        "message": (
            "Este pedido não pode continuar. Para esclarecer a situação, contacte "
            "a equipa NKATA pelo canal oficial."
        ),
        "tone": "closed",
        "stage": 3,
    },
}


def _normalizar_erros(form):
    errors = {}
    for field, messages in form.errors.get_json_data().items():
        readable = []
        for item in messages:
            message = item.get("message", "Revise este campo.")
            if field == "email" and "already exists" in message.lower():
                message = "Já existe um pedido associado a este email."
            readable.append(message)
        errors[field] = readable
    return errors


def _validar_imagem(upload):
    if not upload:
        return "Escolha uma imagem."
    if upload.size > MAX_ACCESS_IMAGE_SIZE:
        return "A imagem deve ter no máximo 6 MB."
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
        image_format = (image.format or "").upper()
        safe_dimensions = image_dimensions_are_safe(image)
        upload.seek(0)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return "O ficheiro escolhido não é uma imagem válida."
    if image_format not in ALLOWED_ACCESS_IMAGE_FORMATS:
        return "Use uma imagem em JPG, PNG ou WEBP."
    if not safe_dimensions:
        return "A imagem possui dimensões demasiado grandes."
    return None


def _identity_email_hash(email):
    return hashlib.sha256(str(email or "").strip().lower().encode("utf-8")).hexdigest()


def _resolve_identity_session(raw_token, email):
    if not raw_token:
        return None, None
    try:
        token = uuid.UUID(str(raw_token).strip())
    except (ValueError, TypeError, AttributeError):
        return None, "A sessão NKATA ID não é válida. Inicie novamente a verificação."

    session = VerificacaoIdentidadeNKATA.objects.filter(token=token).first()
    if (
        not session
        or session.expirada
        or session.pedido_id
        or session.email_hash != _identity_email_hash(email)
        or not session.pode_anexar_ao_pedido
    ):
        return None, "A sessão NKATA ID não está concluída ou já expirou."
    return session, None


def _copy_verified_profile_photo(pedido, verification):
    if not verification.usar_foto_verificada or not verification.selfie_ao_vivo:
        return
    with verification.selfie_ao_vivo.open("rb") as handle:
        content = ContentFile(handle.read())
    extension = os.path.splitext(verification.selfie_ao_vivo.name)[1] or ".jpg"
    pedido.foto_perfil.save(
        f"foto-verificada-{verification.token}{extension}",
        content,
        save=False,
    )
    pedido.save(update_fields=["foto_perfil", "atualizado_em"])


def _status_payload(pedido):
    content = STATUS_CONTENT.get(
        pedido.status,
        {
            "title": "O pedido está a ser acompanhado.",
            "message": "Consulte novamente mais tarde para ver novas atualizações.",
            "tone": "waiting",
            "stage": 1,
        },
    )

    perfil = (
        PerfilNKATA.objects
        .select_related("usuario")
        .filter(pedido=pedido)
        .first()
    )
    can_login = bool(
        pedido.status == "APROVADO"
        and perfil
        and perfil.usuario_id
        and perfil.usuario.has_usable_password()
    )

    message = content["message"]
    if pedido.status == "APROVADO" and can_login:
        message = "A sua conta está pronta. Já pode entrar no NKATA com o email e a palavra-passe que criou."

    verification = getattr(pedido, "verificacao_identidade", None)
    recapture_path = ""
    if (
        pedido.status == "PRECISA_CORRIGIR"
        and verification
        and verification.status == "REPETIR"
    ):
        message = (
            "A equipa pediu novas capturas da identidade. Use a câmara do telefone "
            "para repetir a verificação e depois consulte novamente este pedido."
        )
        recapture_path = f"/verificar-identidade/{verification.token}/"

    return {
        "codigo": str(pedido.token),
        "status": pedido.status,
        "status_label": pedido.get_status_display(),
        "title": content["title"],
        "message": message,
        "tone": content["tone"],
        "stage": content["stage"],
        "created_at": pedido.criado_em,
        "updated_at": pedido.atualizado_em,
        "can_login": can_login,
        "next_action": (
            "LOGIN" if can_login
            else "QUESTIONNAIRE" if pedido.status == "APROVADO"
            else "IDENTITY_RECAPTURE" if recapture_path
            else None
        ),
        "next_path": recapture_path,
    }


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([AccessRequestRateThrottle])
def api_pedir_acesso(request):
    email = str(request.data.get("email", "")).strip().lower()
    identity_session, identity_error = _resolve_identity_session(
        request.data.get("nkata_id_token"),
        email,
    )
    uses_legacy_identity = not request.data.get("nkata_id_token")
    if identity_error:
        return Response({
            "detail": identity_error,
            "errors": {"nkata_id_token": [identity_error]},
        }, status=400)

    image_errors = {}
    safe_files = request.FILES.copy()
    fields_to_validate = IMAGE_FIELDS if uses_legacy_identity else PROFILE_IMAGE_FIELDS
    for field in fields_to_validate:
        upload = request.FILES.get(field)
        error = _validar_imagem(upload)
        if error:
            image_errors[field] = [error]
            continue
        try:
            safe_files[field] = sanitized_image_upload(upload)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
            image_errors[field] = ["Não foi possível preparar esta imagem."]
    if image_errors:
        return Response({
            "detail": "Revise as imagens antes de continuar.",
            "errors": image_errors,
        }, status=400)

    if email and PedidoEntrada.objects.filter(email__iexact=email).exists():
        return Response({
            "detail": "Já recebemos um pedido com este email.",
            "errors": {
                "email": ["Use o mesmo email e o código privado para acompanhar o pedido."]
            },
        }, status=409)

    # Em pedidos multipart, ``request.data`` junta os campos de texto aos
    # UploadedFile. QueryDict.copy() tenta fazer deepcopy desses ficheiros e
    # falha quando o Django os guardou temporariamente no disco (BufferedRandom,
    # comum em fotografias maiores no Python 3.14). O formulário já recebe os
    # ficheiros separadamente em ``safe_files``, por isso copiamos apenas POST.
    data = request.POST.copy() if request.FILES else request.data.copy()
    if email:
        data["email"] = email

    form = PedidoEntradaForm(data, safe_files)
    if not form.is_valid():
        return Response({
            "detail": "Há alguns campos que precisam da sua atenção.",
            "errors": _normalizar_erros(form),
        }, status=400)

    pedido = form.save()
    if identity_session:
        identity_session.pedido = pedido
        identity_session.save(update_fields=["pedido", "atualizado_em"])
        _copy_verified_profile_photo(pedido, identity_session)
    codigo = str(pedido.token)

    return Response({
        "ok": True,
        "pedido_id": pedido.id,
        "codigo": codigo,
        "email": pedido.email,
        "nkata_id_status": identity_session.status if identity_session else "LEGADO",
        "message": (
            "Recebemos o seu pedido. Guarde este código privado para acompanhar "
            f"a análise: {codigo}"
        ),
    }, status=201)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([AccessStatusRateThrottle])
def api_acompanhar_pedido(request):
    email = str(request.data.get("email", "")).strip().lower()
    raw_code = str(request.data.get("codigo", "")).strip()

    if not email or not raw_code:
        return Response(
            {"detail": "Informe o email e o código privado do pedido."},
            status=400,
        )

    try:
        code = uuid.UUID(raw_code)
    except (ValueError, AttributeError, TypeError):
        return Response(
            {"detail": "O email ou o código do pedido não está correto."},
            status=404,
        )

    pedido = PedidoEntrada.objects.filter(email__iexact=email, token=code).first()
    if not pedido:
        return Response(
            {"detail": "O email ou o código do pedido não está correto."},
            status=404,
        )

    return Response(_status_payload(pedido))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([AccessCodeRecoveryRateThrottle])
def api_recuperar_codigo_pedido(request):
    email = str(request.data.get("email", "")).strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return Response({"detail": "Informe o email usado no pedido."}, status=400)

    pedido = (
        PedidoEntrada.objects
        .filter(email__iexact=email)
        .order_by("-criado_em")
        .first()
    )
    if pedido:
        send_access_receipt_email(pedido)

    return Response({
        "ok": True,
        "message": (
            "Se existir um pedido associado a este email, enviámos o código "
            "privado. Verifique também a pasta de spam."
        ),
    })
