from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .post_safety_models import DenunciaPublicacaoNKATA, OcultacaoPublicacaoNKATA
from .posts_api import _feed_queryset, _perfil_do_utilizador
from .posts_models import PublicacaoNKATA


REPORT_REASONS = {
    value: label
    for value, label in DenunciaPublicacaoNKATA.MOTIVO_CHOICES
}


def _visible_publication_for(request, publication_id):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil or perfil.status != "ATIVO":
        return None, perfil

    try:
        publication = _feed_queryset(request.user, perfil).filter(
            id=publication_id,
        ).first()
    except DatabaseError:
        return None, perfil
    return publication, perfil


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def api_ocultar_publicacao(request, publicacao_id):
    publicacao, perfil = _visible_publication_for(request, publicacao_id)
    if not perfil:
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )
    if not publicacao:
        return Response({"detail": "Publicação não disponível."}, status=404)
    if publicacao.usuario_id == request.user.id:
        return Response(
            {"detail": "Use Remover para apagar a sua própria publicação."},
            status=400,
        )

    try:
        OcultacaoPublicacaoNKATA.objects.get_or_create(
            publicacao=publicacao,
            usuario=request.user,
        )
    except DatabaseError:
        return Response(
            {
                "detail": "A segurança das publicações ainda precisa de ser preparada neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    return Response({
        "ok": True,
        "hidden": True,
        "publication_id": publicacao.id,
        "message": "Esta publicação deixou de aparecer no seu feed.",
    })


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def api_denunciar_publicacao(request, publicacao_id):
    if request.method == "GET":
        return Response({
            "reasons": [
                {"value": value, "label": label}
                for value, label in DenunciaPublicacaoNKATA.MOTIVO_CHOICES
            ]
        })

    publicacao, perfil = _visible_publication_for(request, publicacao_id)
    if not perfil:
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )
    if not publicacao:
        return Response({"detail": "Publicação não disponível."}, status=404)
    if publicacao.usuario_id == request.user.id:
        return Response(
            {"detail": "Não pode denunciar a sua própria publicação."},
            status=400,
        )

    motivo = str(request.data.get("motivo", "") or "").strip().upper()
    if motivo not in REPORT_REASONS:
        return Response(
            {"motivo": ["Escolha um motivo disponível no NKATA."]},
            status=400,
        )

    try:
        denuncia, created = DenunciaPublicacaoNKATA.objects.get_or_create(
            publicacao=publicacao,
            denunciante=request.user,
            defaults={"motivo": motivo},
        )
        if not created:
            denuncia.motivo = motivo
            denuncia.estado = "PENDENTE"
            denuncia.analisado_em = None
            denuncia.save(update_fields=["motivo", "estado", "analisado_em"])

        OcultacaoPublicacaoNKATA.objects.get_or_create(
            publicacao=publicacao,
            usuario=request.user,
        )
    except DatabaseError:
        return Response(
            {
                "detail": "A segurança das publicações ainda precisa de ser preparada neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    return Response({
        "ok": True,
        "reported": True,
        "hidden": True,
        "publication_id": publicacao.id,
        "reason": motivo,
        "reason_label": REPORT_REASONS[motivo],
        "message": "Denúncia recebida. A publicação foi ocultada do seu feed e seguirá para análise.",
        "reported_at": timezone.now(),
    }, status=201 if created else 200)
