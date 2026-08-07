import mimetypes
import os
from datetime import timedelta

from PIL import Image, UnidentifiedImageError
from django.db import DatabaseError
from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, MatchPerfil
from .moments_models import MOMENT_LIFETIME_HOURS, MomentoNKATA
from .plan_service import plan_for_user


MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_VIDEO_SIZE = 35 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
VALID_VISIBILITIES = {"TODOS", "MATCHES"}

# Não existe texto livre em Momentos. A API transforma apenas códigos desta
# lista em frases aprovadas previamente pelo NKATA.
MOMENT_CAPTIONS = [
    {"value": "SEM_LEGENDA", "label": "Sem legenda", "text": ""},
    {"value": "DIA_TRANQUILO", "label": "Um dia tranquilo por aqui.", "text": "Um dia tranquilo por aqui."},
    {"value": "BOAS_ENERGIAS", "label": "Boas energias para o dia.", "text": "Boas energias para o dia."},
    {"value": "APROVEITAR_MOMENTO", "label": "A aproveitar um bom momento.", "text": "A aproveitar um bom momento."},
    {"value": "CONHECER_COM_CALMA", "label": "Aberto(a) a conhecer alguém com calma.", "text": "Aberto(a) a conhecer alguém com calma."},
    {"value": "FIM_DE_DIA", "label": "A terminar o dia com tranquilidade.", "text": "A terminar o dia com tranquilidade."},
]
CAPTION_BY_CODE = {item["value"]: item for item in MOMENT_CAPTIONS}


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
    approved = momento.moderacao_status == "APROVADO"
    remaining_seconds = None
    expires_at = None
    if approved:
        remaining_seconds = max(
            0,
            int((momento.expira_em - timezone.now()).total_seconds()),
        )
        expires_at = momento.expira_em

    media_url = (
        request.build_absolute_uri(f"/api/momentos/{momento.id}/media/")
        if momento.media
        else None
    )
    payload = {
        "id": momento.id,
        "profile": _profile_payload(request, momento.perfil),
        "text": momento.texto,
        "media_url": media_url,
        "media_type": momento.tipo_media,
        "visibility": momento.visibilidade,
        "visibility_label": momento.get_visibilidade_display(),
        "mine": momento.usuario_id == request.user.id,
        "moderation_status": momento.moderacao_status,
        "moderation_label": momento.get_moderacao_status_display(),
        "created_at": momento.criado_em,
        "expires_at": expires_at,
        "remaining_seconds": remaining_seconds,
    }
    if payload["mine"] and momento.moderacao_status == "REJEITADO":
        payload["moderation_note"] = (
            momento.moderacao_motivo
            or "Este conteúdo não está de acordo com as regras dos Momentos NKATA."
        )
    return payload


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
        .filter(
            moderacao_status="APROVADO",
            expira_em__gt=timezone.now(),
        )
        .filter(visibility)
        .select_related("perfil", "perfil__pedido", "usuario")
        .order_by("-criado_em")
    )
    if blocked_profile_ids:
        qs = qs.exclude(perfil_id__in=blocked_profile_ids)
    if blocker_user_ids:
        qs = qs.exclude(usuario_id__in=blocker_user_ids)
    return qs


def _review_queryset(user):
    return (
        MomentoNKATA.objects
        .filter(
            usuario=user,
            moderacao_status__in=["PENDENTE", "REJEITADO"],
        )
        .select_related("perfil", "perfil__pedido", "usuario")
        .order_by("-criado_em")[:20]
    )


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
        "free_text_enabled": False,
        "media_enabled": bool(plan["features"].get("status_media", False)),
        "media_requires_moderation": True,
        "expires_hours": MOMENT_LIFETIME_HOURS,
        "caption_options": [
            {"value": item["value"], "label": item["label"]}
            for item in MOMENT_CAPTIONS
        ],
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
            em_revisao = list(_review_queryset(request.user))
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
            "review_items": [_moment_payload(request, momento) for momento in em_revisao],
            "capabilities": _capabilities(request.user),
        })

    # Rejeita explicitamente tentativas de contornar a interface e enviar texto
    # livre diretamente para a API.
    free_text = str(request.data.get("texto", "") or "").strip()
    if free_text:
        return Response(
            {
                "detail": "Momentos não aceitam texto livre. Escolha uma frase NKATA.",
                "code": "free_text_not_allowed",
            },
            status=400,
        )

    caption_code = str(
        request.data.get("legenda", "SEM_LEGENDA") or "SEM_LEGENDA"
    ).strip().upper()
    caption = CAPTION_BY_CODE.get(caption_code)
    if not caption:
        return Response(
            {"legenda": ["Escolha uma frase disponível no NKATA."]},
            status=400,
        )

    visibilidade = str(
        request.data.get("visibilidade", "TODOS") or "TODOS"
    ).strip().upper()
    media = request.FILES.get("media")

    if visibilidade not in VALID_VISIBILITIES:
        return Response(
            {"visibilidade": ["Escolha uma opção de privacidade válida."]},
            status=400,
        )
    if not caption["text"] and not media:
        return Response(
            {"detail": "Escolha uma frase NKATA ou uma fotografia/vídeo."},
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

    # Frases predefinidas sem media podem ser publicadas imediatamente porque
    # o utilizador não controla o conteúdo textual. Foto/vídeo entra sempre na
    # fila de moderação e as 24 horas só começam após aprovação.
    moderation_status = "PENDENTE" if media else "APROVADO"
    expires_at = timezone.now() + timedelta(hours=MOMENT_LIFETIME_HOURS)

    try:
        momento = MomentoNKATA.objects.create(
            perfil=perfil,
            usuario=request.user,
            texto=caption["text"],
            media=media or "",
            tipo_media=tipo_media or "TEXTO",
            visibilidade=visibilidade,
            moderacao_status=moderation_status,
            moderacao_motivo="",
            moderado_em=None if media else timezone.now(),
            expira_em=expires_at,
        )
    except DatabaseError:
        return Response(
            {
                "detail": "Os Momentos ainda precisam de ser preparados neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    pending = moderation_status == "PENDENTE"
    return Response(
        {
            "ok": True,
            "pending_review": pending,
            "message": (
                "Foto/vídeo enviado para análise. As 24 horas começam apenas depois da aprovação."
                if pending
                else "Momento publicado. Fica disponível durante 24 horas."
            ),
            "moment": _moment_payload(request, momento),
            "capabilities": capabilities,
        },
        status=202 if pending else 201,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_media_momento(request, momento_id):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil and not request.user.is_staff:
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    try:
        if request.user.is_staff:
            momento = MomentoNKATA.objects.filter(id=momento_id).first()
        else:
            # O autor pode rever o próprio ficheiro pendente/rejeitado.
            momento = MomentoNKATA.objects.filter(
                id=momento_id,
                usuario=request.user,
            ).first()
            if not momento:
                momento = _feed_queryset(request.user, perfil).filter(id=momento_id).first()
    except DatabaseError:
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    if not momento or not momento.media:
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    try:
        file_handle = momento.media.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    content_type = mimetypes.guess_type(momento.media.name)[0] or "application/octet-stream"
    response = FileResponse(file_handle, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(momento.media.name)}"'
    response["Cache-Control"] = "private, max-age=120"
    response["X-Content-Type-Options"] = "nosniff"
    return response


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
