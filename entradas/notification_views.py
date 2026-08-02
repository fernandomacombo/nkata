from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .notification_models import NotificacaoNKATA
from .notification_serializers import NotificacaoSerializer


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_notificacoes(request):
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

    return Response({
        "count": len(serializer.data),
        "unread": sum(1 for item in serializer.data if not item["lida"]),
        "results": serializer.data,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_marcar_notificacao_lida(request, notificacao_id):
    atualizadas = NotificacaoNKATA.objects.filter(
        id=notificacao_id,
        destinatario=request.user,
    ).update(lida=True)

    if not atualizadas:
        return Response({"detail": "Notificação não encontrada."}, status=404)

    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_marcar_todas_notificacoes_lidas(request):
    atualizadas = NotificacaoNKATA.objects.filter(
        destinatario=request.user,
        lida=False,
    ).update(lida=True)

    return Response({
        "ok": True,
        "updated": atualizadas,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_marcar_notificacoes_match_lidas(request, match_id):
    atualizadas = NotificacaoNKATA.objects.filter(
        destinatario=request.user,
        match_id=match_id,
        lida=False,
    ).update(lida=True)

    return Response({
        "ok": True,
        "updated": atualizadas,
    })
