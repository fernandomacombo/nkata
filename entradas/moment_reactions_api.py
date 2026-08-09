from django.db import DatabaseError
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .moment_reaction_service import (
    REACTION_BY_CODE,
    reaction_payload,
    toggle_reaction,
)
from .moments_api import _feed_queryset, _perfil_do_utilizador


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_reacoes_momento(request, momento_id):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil or perfil.status != "ATIVO":
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    try:
        momento = _feed_queryset(request.user, perfil).filter(id=momento_id).first()
    except DatabaseError:
        return Response({"detail": "Conteúdo não disponível."}, status=404)

    if not momento:
        return Response({"detail": "Momento não encontrado."}, status=404)

    if request.method == "GET":
        payload = reaction_payload(request.user, momento)
        return Response({
            "moment_id": momento.id,
            "reactions": payload,
        })

    if momento.usuario_id == request.user.id:
        return Response(
            {"detail": "Não pode reagir ao seu próprio Momento."},
            status=400,
        )

    reaction_type = str(request.data.get("tipo", "") or "").strip().upper()
    if reaction_type not in REACTION_BY_CODE:
        return Response(
            {"tipo": ["Escolha uma reação disponível no NKATA."]},
            status=400,
        )

    try:
        active, current = toggle_reaction(
            request.user,
            perfil,
            momento,
            reaction_type,
        )
        payload = reaction_payload(request.user, momento)
    except DatabaseError:
        return Response(
            {
                "detail": "As reações dos Momentos ainda precisam de ser preparadas neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    return Response({
        "ok": True,
        "active": active,
        "mine": current,
        "message": "Reação enviada." if active else "Reação removida.",
        "reactions": payload,
    })
