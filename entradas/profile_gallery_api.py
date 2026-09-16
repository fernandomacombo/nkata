from django.db import DatabaseError
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .posts_api import _feed_queryset
from .posts_models import PublicacaoNKATA
from .user_roles import active_member_profile_for_user


PROFILE_GALLERY_LIMIT = 18


def _perfil_do_utilizador(user):
    return active_member_profile_for_user(user)


def _gallery_item(publicacao, cover_id=None):
    return {
        "id": publicacao.id,
        "media_url": f"/api/publicacoes/{publicacao.id}/media/",
        "media_type": publicacao.tipo_media,
        "caption": publicacao.legenda,
        "visibility": publicacao.visibilidade,
        "created_at": publicacao.criado_em,
        "is_cover": publicacao.id == cover_id,
        "can_be_cover": (
            publicacao.tipo_media == "IMAGEM"
            and publicacao.visibilidade == "TODOS"
        ),
    }


def gallery_for_profile_viewer(request, perfil):
    viewer_profile = _perfil_do_utilizador(request.user)
    if not viewer_profile:
        return {"cover_url": None, "gallery": [], "gallery_count": 0}

    try:
        publications = list(
            _feed_queryset(request.user, viewer_profile)
            .filter(perfil_id=perfil.id)[:PROFILE_GALLERY_LIMIT]
        )
    except DatabaseError:
        return {"cover_url": None, "gallery": [], "gallery_count": 0}

    items = [_gallery_item(item, perfil.capa_publicacao_id) for item in publications]
    cover = next((item for item in items if item["is_cover"]), None)
    return {
        "cover_url": cover["media_url"] if cover else None,
        "gallery": items,
        "gallery_count": len(items),
    }


def _own_approved_publications(perfil, user):
    return (
        PublicacaoNKATA.objects
        .filter(
            perfil=perfil,
            usuario=user,
            moderacao_status="APROVADO",
        )
        .order_by("-criado_em")
    )


def _own_gallery_payload(perfil, user):
    publications = list(
        _own_approved_publications(perfil, user)[:PROFILE_GALLERY_LIMIT]
    )
    items = [_gallery_item(item, perfil.capa_publicacao_id) for item in publications]
    cover = next((item for item in items if item["is_cover"]), None)
    return {
        "count": len(items),
        "cover_publication_id": cover["id"] if cover else None,
        "cover_url": cover["media_url"] if cover else None,
        "results": items,
    }


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_minha_galeria(request):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    try:
        return Response(_own_gallery_payload(perfil, request.user))
    except DatabaseError:
        return Response(
            {"detail": "A galeria ainda não está disponível neste ambiente."},
            status=503,
        )


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def api_minha_capa(request):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    publication_id = request.data.get("publication_id")
    if publication_id in (None, ""):
        perfil.capa_publicacao_id = None
        perfil.save(update_fields=["capa_publicacao_id", "atualizado_em"])
        return Response({
            "ok": True,
            "message": "Capa removida.",
            "gallery": _own_gallery_payload(perfil, request.user),
        })

    try:
        publication_id = int(publication_id)
    except (TypeError, ValueError):
        return Response({"publication_id": ["Escolha uma fotografia válida."]}, status=400)

    try:
        publication = _own_approved_publications(perfil, request.user).filter(
            id=publication_id,
            tipo_media="IMAGEM",
            visibilidade="TODOS",
        ).first()
    except DatabaseError:
        return Response(
            {"detail": "A galeria ainda não está disponível neste ambiente."},
            status=503,
        )

    if not publication:
        return Response(
            {
                "publication_id": [
                    "Use uma fotografia aprovada e visível para todos os membros."
                ]
            },
            status=400,
        )

    perfil.capa_publicacao_id = publication.id
    perfil.save(update_fields=["capa_publicacao_id", "atualizado_em"])
    return Response({
        "ok": True,
        "message": "Capa atualizada.",
        "gallery": _own_gallery_payload(perfil, request.user),
    })
