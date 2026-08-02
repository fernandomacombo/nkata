from django.db import DatabaseError
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .notification_models import NotificacaoNKATA
from .notification_serializers import NotificacaoSerializer


def _notification_setup_response():
    return Response({
        "count": 0,
        "unread": 0,
        "results": [],
        "setup_required": True,
        "message": "As notificações estão a ser preparadas.",
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_notificacoes(request):
    try:
        notificacoes = (
            NotificacaoNKATA.objects
            .filter(destinatario=request.user)
            .select_related(
                "ator",
                "perfil",
                "perfil__pedido",
                "perfil__usuario",
                "match",
            )
            .order_by("-atualizado_em")[:100]
        )

        serializer = NotificacaoSerializer(
            notificacoes,
            many=True,
            context={"request": request},
        )
        results = serializer.data
    except DatabaseError:
        return _notification_setup_response()

    return Response({
        "count": len(results),
        "unread": sum(1 for item in results if not item["lida"]),
        "results": results,
        "setup_required": False,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_marcar_notificacao_lida(request, notificacao_id):
    try:
        atualizadas = NotificacaoNKATA.objects.filter(
            id=notificacao_id,
            destinatario=request.user,
        ).update(lida=True)
    except DatabaseError:
        return Response({"ok": True, "setup_required": True})

    if not atualizadas:
        return Response({"detail": "Notificação não encontrada."}, status=404)

    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_marcar_todas_notificacoes_lidas(request):
    try:
        atualizadas = NotificacaoNKATA.objects.filter(
            destinatario=request.user,
            lida=False,
        ).update(lida=True)
    except DatabaseError:
        return Response({"ok": True, "updated": 0, "setup_required": True})

    return Response({
        "ok": True,
        "updated": atualizadas,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_marcar_notificacoes_match_lidas(request, match_id):
    try:
        atualizadas = NotificacaoNKATA.objects.filter(
            destinatario=request.user,
            match_id=match_id,
            lida=False,
        ).update(lida=True)
    except DatabaseError:
        return Response({"ok": True, "updated": 0, "setup_required": True})

    return Response({
        "ok": True,
        "updated": atualizadas,
    })
