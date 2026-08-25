import json
import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .notification_models import NotificacaoNKATA, PushSubscriptionNKATA


logger = logging.getLogger(__name__)


def push_configured():
    return bool(
        settings.NKATA_WEBPUSH_PUBLIC_KEY
        and settings.NKATA_WEBPUSH_PRIVATE_KEY
        and settings.NKATA_WEBPUSH_SUBJECT
    )


def _notification_url(notification):
    if notification.match_id:
        return f"/matches/{notification.match_id}/conversa/"
    return "/notificacoes/"


def send_push_notification(notification):
    if not push_configured():
        return 0

    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush não está instalado; push ignorado.")
        return 0

    payload = json.dumps({
        "title": notification.titulo,
        "body": notification.texto,
        "tag": f"nkata-{notification.tipo.lower()}-{notification.chave}",
        "url": _notification_url(notification),
        "icon": "/icons/nkata-192.png",
        "renotify": notification.tipo in {"MATCH", "MENSAGEM"},
    }, ensure_ascii=False)

    delivered = 0
    subscriptions = PushSubscriptionNKATA.objects.filter(
        destinatario_id=notification.destinatario_id,
        ativa=True,
    )
    for subscription in subscriptions.iterator():
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {
                        "p256dh": subscription.p256dh,
                        "auth": subscription.auth,
                    },
                },
                data=payload,
                vapid_private_key=settings.NKATA_WEBPUSH_PRIVATE_KEY,
                vapid_claims={"sub": settings.NKATA_WEBPUSH_SUBJECT},
                ttl=settings.NKATA_WEBPUSH_TTL,
                timeout=6,
            )
            delivered += 1
        except WebPushException as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in {404, 410}:
                PushSubscriptionNKATA.objects.filter(pk=subscription.pk).update(ativa=False)
            logger.warning(
                "Falha ao enviar Web Push NKATA (status=%s): %s",
                status_code,
                exc,
            )
        except Exception:  # noqa: BLE001 - push nunca invalida a ação principal
            logger.exception("Falha inesperada ao enviar Web Push NKATA.")

    return delivered


@receiver(post_save, sender=NotificacaoNKATA)
def enviar_push_da_notificacao(sender, instance, **kwargs):
    if instance.lida:
        return
    send_push_notification(instance)
