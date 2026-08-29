import mimetypes
import os

from PIL import Image, UnidentifiedImageError
from django.db import DatabaseError
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .content_moderation_queue import queue_content_media_analysis
from .identity_models import pedido_tem_identidade_verificada
from .media_validation import image_dimensions_are_safe, sanitized_image_upload
from .models import AcaoPerfil, MatchPerfil, PerfilNKATA
from .plan_service import plan_for_user
from .post_reaction_service import reaction_payload, toggle_reaction
from .post_safety_models import OcultacaoPublicacaoNKATA
from .posts_models import PublicacaoNKATA
from .profile_media_api import profile_photo_url


MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_VIDEO_SIZE = 60 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
VALID_VISIBILITIES = {"TODOS", "MATCHES"}

POST_CAPTIONS = [
    {"value": "SEM_LEGENDA", "label": "Sem legenda", "text": ""},
    {"value": "UM_POUCO_DE_MIM", "label": "Um pouco de mim.", "text": "Um pouco de mim."},
    {"value": "BOM_MOMENTO", "label": "Um bom momento para guardar.", "text": "Um bom momento para guardar."},
    {"value": "DIA_ESPECIAL", "label": "Um dia especial por aqui.", "text": "Um dia especial por aqui."},
    {"value": "VIDA_COM_CALMA", "label": "A viver com calma e intenção.", "text": "A viver com calma e intenção."},
    {"value": "CONHECER_COM_RESPEITO", "label": "Aberto(a) a conhecer alguém com respeito.", "text": "Aberto(a) a conhecer alguém com respeito."},
]
CAPTION_BY_CODE = {item["value"]: item for item in POST_CAPTIONS}


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


def _profile_payload(request, perfil):
    return {
        "id": perfil.id,
        "nome_publico": perfil.nome_publico,
        "cidade": perfil.cidade,
        "idade": perfil.idade,
        "objetivo_display": perfil.get_objetivo_display(),
        "foto_url": profile_photo_url(perfil),
        "verificado": pedido_tem_identidade_verificada(perfil.pedido),
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


def _followed_profile_ids(user):
    return set(
        AcaoPerfil.objects.filter(
            usuario=user,
            tipo="SEGUIR",
        ).values_list("perfil_id", flat=True)
    )


def _interest_profile_ids(user):
    return set(
        AcaoPerfil.objects.filter(
            usuario=user,
            tipo="INTERESSE",
        ).values_list("perfil_id", flat=True)
    )


def _hidden_publication_ids(user):
    return set(
        OcultacaoPublicacaoNKATA.objects.filter(
            usuario=user,
        ).values_list("publicacao_id", flat=True)
    )


def _feed_queryset(user, perfil):
    matched_ids = _matched_profile_ids(perfil)
    followed_ids = _followed_profile_ids(user)
    hidden_publication_ids = _hidden_publication_ids(user)
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

    priority_cases = [When(usuario=user, then=Value(0))]
    if followed_ids:
        priority_cases.append(When(perfil_id__in=followed_ids, then=Value(1)))

    qs = (
        PublicacaoNKATA.objects
        .filter(moderacao_status="APROVADO")
        .filter(visibility)
        .select_related("perfil", "perfil__pedido", "usuario")
        .annotate(
            relationship_priority=Case(
                *priority_cases,
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("relationship_priority", "-criado_em")
    )

    if hidden_publication_ids:
        qs = qs.exclude(id__in=hidden_publication_ids)
    if blocked_profile_ids:
        qs = qs.exclude(perfil_id__in=blocked_profile_ids)
    if blocker_user_ids:
        qs = qs.exclude(usuario_id__in=blocker_user_ids)
    return qs


def _review_queryset(user):
    return (
        PublicacaoNKATA.objects
        .filter(
            usuario=user,
            moderacao_status__in=["PENDENTE", "REJEITADO"],
        )
        .select_related("perfil", "perfil__pedido", "usuario")
        .order_by("-criado_em")[:20]
    )


def _can_view_publication(user, perfil, publicacao):
    if publicacao.usuario_id == user.id:
        return publicacao.moderacao_status in {"PENDENTE", "APROVADO", "REJEITADO"}
    return _feed_queryset(user, perfil).filter(id=publicacao.id).exists()


def _publication_payload(request, publicacao, *, followed_ids=None, interest_ids=None):
    mine = publicacao.usuario_id == request.user.id
    followed_ids = followed_ids if followed_ids is not None else _followed_profile_ids(request.user)
    interest_ids = interest_ids if interest_ids is not None else _interest_profile_ids(request.user)

    return {
        "id": publicacao.id,
        "profile": _profile_payload(request, publicacao.perfil),
        # Mantém a mídia no mesmo origin do frontend. Em desenvolvimento o
        # Vite encaminha /api ao Django; em produção ambos usam o mesmo host.
        "media_url": f"/api/publicacoes/{publicacao.id}/media/",
        "media_type": publicacao.tipo_media,
        "caption": publicacao.legenda,
        "visibility": publicacao.visibilidade,
        "visibility_label": publicacao.get_visibilidade_display(),
        "mine": mine,
        "following": publicacao.perfil_id in followed_ids,
        "interest_active": publicacao.perfil_id in interest_ids,
        "moderation_status": publicacao.moderacao_status,
        "moderation_label": publicacao.get_moderacao_status_display(),
        "moderation_note": (
            publicacao.moderacao_motivo
            if mine and publicacao.moderacao_status == "REJEITADO"
            else ""
        ),
        "created_at": publicacao.criado_em,
        "reactions": reaction_payload(request.user, publicacao),
    }


def _validate_media(file_obj):
    if not file_obj:
        return None, "Escolha uma fotografia ou vídeo para publicar."

    extension = os.path.splitext(file_obj.name or "")[1].lower()
    content_type = str(getattr(file_obj, "content_type", "") or "").lower()

    if content_type.startswith("image/") or extension in ALLOWED_IMAGE_EXTENSIONS:
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            return None, "Use uma imagem JPG, PNG ou WEBP."
        if file_obj.size > MAX_IMAGE_SIZE:
            return None, "A imagem deve ter no máximo 10 MB."
        try:
            image = Image.open(file_obj)
            if not image_dimensions_are_safe(image):
                file_obj.seek(0)
                return None, "A imagem possui dimensões demasiado grandes."
            image.verify()
            file_obj.seek(0)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
            return None, "O ficheiro enviado não é uma imagem válida."
        return "IMAGEM", None

    if content_type.startswith("video/") or extension in ALLOWED_VIDEO_EXTENSIONS:
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            return None, "Use um vídeo MP4, WEBM ou MOV."
        if file_obj.size > MAX_VIDEO_SIZE:
            return None, "O vídeo deve ter no máximo 60 MB."
        return "VIDEO", None

    return None, "Use uma imagem JPG/PNG/WEBP ou um vídeo MP4/WEBM/MOV."


def _capabilities(user):
    plan = plan_for_user(user)
    return {
        "plan": plan["code"],
        "plan_label": plan["label"],
        "view_enabled": bool(plan["features"].get("feed_view", True)),
        "publish_media_enabled": bool(plan["features"].get("feed_media_publish", False)),
        "media_requires_moderation": True,
        "free_text_enabled": False,
        "caption_options": [
            {"value": item["value"], "label": item["label"]}
            for item in POST_CAPTIONS
        ],
        "visibility_options": [
            {"value": "TODOS", "label": "Todos os membros"},
            {"value": "MATCHES", "label": "Apenas matches"},
        ],
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_publicacoes(request):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil or perfil.status != "ATIVO":
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )

    if request.method == "GET":
        try:
            followed_ids = _followed_profile_ids(request.user)
            interest_ids = _interest_profile_ids(request.user)
            publicacoes = list(_feed_queryset(request.user, perfil)[:60])
            em_revisao = list(_review_queryset(request.user))
        except DatabaseError:
            return Response(
                {
                    "detail": "As publicações ainda precisam de ser preparadas neste ambiente.",
                    "setup_required": True,
                },
                status=503,
            )

        return Response({
            "results": [
                _publication_payload(
                    request,
                    item,
                    followed_ids=followed_ids,
                    interest_ids=interest_ids,
                )
                for item in publicacoes
            ],
            "review_items": [
                _publication_payload(
                    request,
                    item,
                    followed_ids=followed_ids,
                    interest_ids=interest_ids,
                )
                for item in em_revisao
            ],
            "capabilities": _capabilities(request.user),
        })

    capabilities = _capabilities(request.user)
    if not capabilities["publish_media_enabled"]:
        return Response(
            {
                "detail": "Publicar fotografias e vídeos exige NKATA Essencial ou Premium.",
                "code": "paid_plan_required_for_publication",
                "capabilities": capabilities,
            },
            status=403,
        )

    free_text = str(request.data.get("texto", "") or "").strip()
    if free_text:
        return Response(
            {
                "detail": "Publicações não aceitam texto livre. Escolha uma frase NKATA.",
                "code": "free_text_not_allowed",
            },
            status=400,
        )

    caption_code = str(
        request.data.get("legenda", "SEM_LEGENDA") or "SEM_LEGENDA"
    ).strip().upper()
    caption = CAPTION_BY_CODE.get(caption_code)
    if not caption:
        return Response({"legenda": ["Escolha uma frase disponível no NKATA."]}, status=400)

    visibilidade = str(
        request.data.get("visibilidade", "TODOS") or "TODOS"
    ).strip().upper()
    if visibilidade not in VALID_VISIBILITIES:
        return Response(
            {"visibilidade": ["Escolha uma opção de privacidade válida."]},
            status=400,
        )

    media = request.FILES.get("media")
    tipo_media, media_error = _validate_media(media)
    if media_error:
        return Response({"media": [media_error]}, status=400)
    if tipo_media == "IMAGEM":
        try:
            media = sanitized_image_upload(media)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
            return Response({"media": ["Não foi possível preparar esta imagem."]}, status=400)

    try:
        publicacao = PublicacaoNKATA.objects.create(
            perfil=perfil,
            usuario=request.user,
            media=media,
            tipo_media=tipo_media,
            legenda=caption["text"],
            visibilidade=visibilidade,
            moderacao_status="PENDENTE",
        )
    except DatabaseError:
        return Response(
            {
                "detail": "As publicações ainda precisam de ser preparadas neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    queued = queue_content_media_analysis(
        content_type="PUBLICACAO",
        content_id=publicacao.id,
        media_type=publicacao.tipo_media,
    )

    return Response(
        {
            "ok": True,
            "pending_review": True,
            "analysis_queued": queued,
            "message": "Publicação enviada para análise. Só aparece no feed depois da aprovação.",
            "publication": _publication_payload(request, publicacao),
            "capabilities": capabilities,
        },
        status=202,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_media_publicacao(request, publicacao_id):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil and not request.user.is_staff:
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    try:
        publicacao = PublicacaoNKATA.objects.select_related("perfil", "usuario").filter(
            id=publicacao_id
        ).first()
        if not publicacao:
            return Response({"detail": "Conteúdo não disponível."}, status=404)

        if not request.user.is_staff and not _can_view_publication(request.user, perfil, publicacao):
            return Response({"detail": "Conteúdo não disponível."}, status=404)
    except DatabaseError:
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    try:
        file_handle = publicacao.media.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    content_type = mimetypes.guess_type(publicacao.media.name)[0] or "application/octet-stream"
    response = FileResponse(file_handle, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(publicacao.media.name)}"'
    response["Cache-Control"] = "private, max-age=120"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["X-Robots-Tag"] = "noindex, noimageindex, noarchive"
    return response


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_reacoes_publicacao(request, publicacao_id):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil or perfil.status != "ATIVO":
        return Response({"detail": "Interação não disponível."}, status=403)

    try:
        publicacao = PublicacaoNKATA.objects.select_related("perfil", "usuario").filter(
            id=publicacao_id,
            moderacao_status="APROVADO",
        ).first()
        if not publicacao or not _feed_queryset(request.user, perfil).filter(id=publicacao_id).exists():
            return Response({"detail": "Publicação não encontrada."}, status=404)
    except DatabaseError:
        return Response({"detail": "Reações indisponíveis neste ambiente."}, status=503)

    if request.method == "GET":
        return Response(reaction_payload(request.user, publicacao))

    if publicacao.usuario_id == request.user.id:
        return Response({"detail": "Não pode reagir à sua própria publicação."}, status=403)

    reaction_type = str(request.data.get("tipo", "") or "").strip().upper()
    try:
        active, selected = toggle_reaction(
            request.user,
            perfil,
            publicacao,
            reaction_type,
        )
    except ValueError:
        return Response({"detail": "Escolha uma reação disponível no NKATA."}, status=400)
    except DatabaseError:
        return Response({"detail": "Reações indisponíveis neste ambiente."}, status=503)

    payload = reaction_payload(request.user, publicacao)
    payload.update({"ok": True, "active": active, "selected": selected})
    return Response(payload)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def api_apagar_publicacao(request, publicacao_id):
    try:
        publicacao = PublicacaoNKATA.objects.filter(
            id=publicacao_id,
            usuario=request.user,
        ).first()
    except DatabaseError:
        return Response({"detail": "Publicações indisponíveis neste ambiente."}, status=503)

    if not publicacao:
        return Response({"detail": "Publicação não encontrada."}, status=404)

    media = publicacao.media
    storage = media.storage if media else None
    media_name = media.name if media else ""
    PerfilNKATA.objects.filter(capa_publicacao_id=publicacao.id).update(
        capa_publicacao_id=None,
    )
    publicacao.delete()
    if storage and media_name:
        try:
            storage.delete(media_name)
        except OSError:
            pass

    return Response({"ok": True, "message": "Publicação removida."})
