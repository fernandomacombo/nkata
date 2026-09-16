from urllib.parse import urlparse

from django.conf import settings
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .notification_models import PushSubscriptionNKATA
from .push_notifications import push_configured


def _valid_endpoint(value):
    if not isinstance(value, str) or len(value) > 4096:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def api_push_subscription(request):
    if request.method == "GET":
        return Response({
            "supported": push_configured(),
            "public_key": settings.NKATA_WEBPUSH_PUBLIC_KEY if push_configured() else "",
            "subscribed": PushSubscriptionNKATA.objects.filter(
                destinatario=request.user,
                ativa=True,
            ).exists(),
        })

    endpoint = request.data.get("endpoint", "")
    if not _valid_endpoint(endpoint):
        return Response({"detail": "Subscrição push inválida."}, status=400)

    if request.method == "DELETE":
        updated = PushSubscriptionNKATA.objects.filter(
            destinatario=request.user,
            endpoint=endpoint,
        ).update(ativa=False)
        return Response({"ok": True, "subscribed": False, "updated": updated})

    if not push_configured():
        return Response(
            {"detail": "As notificações push ainda não foram configuradas no servidor."},
            status=503,
        )

    keys = request.data.get("keys") or {}
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")
    if not p256dh or not auth or len(p256dh) > 255 or len(auth) > 255:
        return Response({"detail": "Chaves da subscrição push inválidas."}, status=400)

    subscription, _ = PushSubscriptionNKATA.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "destinatario": request.user,
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": request.headers.get("User-Agent", "")[:320],
            "ativa": True,
        },
    )
    stale_ids = list(
        PushSubscriptionNKATA.objects.filter(
            destinatario=request.user,
            ativa=True,
        )
        .exclude(pk=subscription.pk)
        .order_by("-atualizado_em")
        .values_list("pk", flat=True)[4:]
    )
    if stale_ids:
        PushSubscriptionNKATA.objects.filter(pk__in=stale_ids).update(ativa=False)
    return Response({"ok": True, "subscribed": subscription.ativa})
