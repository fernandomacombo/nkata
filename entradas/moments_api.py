import os

from PIL import Image, UnidentifiedImageError
from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, MatchPerfil
from .moments_models import MomentoNKATA
from .plan_service import plan_for_user


MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_VIDEO_SIZE = 35 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
VALID_VISIBILITIES = {"TODOS", "MATCHES"}


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


def _absolute_file_url(request, file_field):
    if not file_field:
        return None
    try:
        return request.build_absolute_uri(file_field.url)
    except (ValueError, AttributeError):
        return None


def _profile_payload(request, perfil):
    return {
        "id": perfil.id,
        "nome_publico": perfil.nome_publico,
        "cidade": perfil.cidade,
        "foto_url": _absolute_file_url(request, perfil.foto_principal),
        "verificado": perfil.pedido.status == "APROVADO",
    }


def _moment_payload(request, momento):
    remaining_seconds = max(
        0,
        int((momento.expira_em - timezone.now()).total_seconds()),
    )
    return {
        "id": momento.id,
        "profile": _profile_payload(request, momento.perfil),
        "text": momento.texto,
        "media_url": _absolute_file_url(request, momento.media),
        "media_type": momento.tipo_media,
        "visibility": momento.visibilidade,
        "visibility_label": momento.get_visibilidade_display(),
        "mine": momento.usuario_id == request.user.id,
        "created_at": momento.criado_em,
        "expires_at": momento.expira_em,
        "remaining_seconds": remaining_seconds,
    }


def _matched_profile_ids(perfil):
    ids = set()
    matches = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        status="ATIVO",
    ).values_list("perfil_1_id", "perfil_2_id")
    for perfil_1_id, perfil_2_id in matches:
        ids.add(perfil_2_id if perfil_1_id == perfil.id else perfil_1_id)
    return ids


def _feed_queryset(user, perfil):
    matched_ids = _matched_profile_ids(perfil)
    blocked_profile_ids = set(
        AcaoPerfil.objects.filter(
            usuario=user,
            tipo="BLOQUEIO",
        ).values_list("perfil_id", flat=True)
    )
    blocker_user_ids = set(
        AcaoPerfil.objects.filter(
            perfil=perfil,
            tipo="BLOQUEIO",
            usuario__isnull=False,
        ).values_list("usuario_id", flat=True)
    )

    visibility = Q(usuario=user)
    visibility |= Q(
        visibilidade="TODOS",
        perfil__status="ATIVO",
        perfil__visivel=True,
    )
    if matched_ids:
        visibility |= Q(
            visibilidade="MATCHES",
            perfil_id__in=matched_ids,
            perfil__status="ATIVO",
            perfil__visivel=True,
        )

    qs = (
        MomentoNKATA.objects
        .filter(expira_em__gt=timezone.now())
        .filter(visibility)
        .select_related("perfil", "perfil__pedido", "usuario")
        .order_by("-criado_em")
    )
    if blocked_profile_ids:
        qs = qs.exclude(perfil_id__in=blocked_profile_ids)
    if blocker_user_ids:
        qs = qs.exclude(usuario_id__in=blocker_user_ids)
    return qs


def _validate_media(file_obj):
    if not file_obj:
        return None, None

    extension = os.path.splitext(file_obj.name or "")[1].lower()
    content_type = str(getattr(file_obj, "content_type", "") or "").lower()

    if content_type.startswith("image/") or extension in ALLOWED_IMAGE_EXTENSIONS:
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            return None, "Use uma imagem JPG, PNG ou WEBP."
        if file_obj.size > MAX_IMAGE_SIZE:
            return None, "A imagem deve ter no máximo 8 MB."
        try:
            image = Image.open(file_obj)
            image.verify()
            file_obj.seek(0)
        except (UnidentifiedImageError, OSError, ValueError):
            return None, "O ficheiro enviado não é uma imagem válida."
        return "IMAGEM", None

    if content_type.startswith("video/") or extension in ALLOWED_VIDEO_EXTENSIONS:
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            return None, "Use um vídeo MP4, WEBM ou MOV."
        if file_obj.size > MAX_VIDEO_SIZE:
            return None, "O vídeo deve ter no máximo 35 MB."
        return "VIDEO", None

    return None, "Use uma imagem JPG/PNG/WEBP ou um vídeo MP4/WEBM/MOV."


def _capabilities(user):
    plan = plan_for_user(user)
    return {
        "plan": plan["code"],
        "plan_label": plan["label"],
        "text_enabled": bool(plan["features"].get("status_text", True)),
        "media_enabled": bool(plan["features"].get("status_media", False)),
        "max_text_length": 500,
        "expires_hours": 24,
        "visibility_options": [
            {"value": "TODOS", "label": "Todos os membros"},
            {"value": "MATCHES", "label": "Apenas matches"},
        ],
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_momentos(request):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil or perfil.status != "ATIVO":
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )

    if request.method == "GET":
        try:
            momentos = list(_feed_queryset(request.user, perfil))
        except DatabaseError:
            return Response(
                {
                    "detail": "Os Momentos ainda precisam de ser preparados neste ambiente.",
                    "setup_required": True,
                },
                status=503,
            )

        payloads = [_moment_payload(request, momento) for momento in momentos]
        return Response({
            "results": payloads,
            "mine": [item for item in payloads if item["mine"]],
            "capabilities": _capabilities(request.user),
        })

    texto = " ".join(str(request.data.get("texto", "") or "").split()).strip()
    visibilidade = str(request.data.get("visibilidade", "TODOS") or "TODOS").strip().upper()
    media = request.FILES.get("media")

    if len(texto) > 500:
        return Response({"texto": ["O texto deve ter no máximo 500 caracteres."]}, status=400)
    if visibilidade not in VALID_VISIBILITIES:
        return Response({"visibilidade": ["Escolha uma opção de privacidade válida."]}, status=400)
    if not texto and not media:
        return Response(
            {"detail": "Escreva algo ou escolha uma fotografia/vídeo."},
            status=400,
        )

    tipo_media, media_error = _validate_media(media)
    if media_error:
        return Response({"media": [media_error]}, status=400)

    capabilities = _capabilities(request.user)
    if media and not capabilities["media_enabled"]:
        return Response(
            {
                "detail": "Fotografias e vídeos nos Momentos exigem um plano pago.",
                "code": "paid_plan_required_for_moment_media",
                "capabilities": capabilities,
            },
            status=403,
        )

    try:
        momento = MomentoNKATA.objects.create(
            perfil=perfil,
            usuario=request.user,
            texto=texto,
            media=media or "",
            tipo_media=tipo_media or "TEXTO",
            visibilidade=visibilidade,
        )
    except DatabaseError:
        return Response(
            {
                "detail": "Os Momentos ainda precisam de ser preparados neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    return Response(
        {
            "ok": True,
            "message": "Momento publicado. Fica disponível durante 24 horas.",
            "moment": _moment_payload(request, momento),
            "capabilities": capabilities,
        },
        status=201,
    )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def api_apagar_momento(request, momento_id):
    try:
        momento = MomentoNKATA.objects.filter(
            id=momento_id,
            usuario=request.user,
        ).first()
    except DatabaseError:
        return Response({"detail": "Momentos indisponíveis neste ambiente."}, status=503)

    if not momento:
        return Response({"detail": "Momento não encontrado."}, status=404)

    media = momento.media
    storage = media.storage if media else None
    media_name = media.name if media else ""
    momento.delete()
    if storage and media_name:
        try:
            storage.delete(media_name)
        except OSError:
            pass

    return Response({"ok": True, "message": "Momento removido."})
