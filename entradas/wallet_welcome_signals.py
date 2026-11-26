"""Grant after committed identity changes; the backfill command covers retries."""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .identity_models import VerificacaoIdentidadeNKATA
from .models import PedidoEntrada, PerfilNKATA
from .wallet_service import grant_welcome_credits, WalletError

logger = logging.getLogger(__name__)


def _after_commit(user_id):
    if not settings.NKATA_CREDIT_TRANSITION_ENABLED or not user_id:
        return
    def grant():
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            try:
                grant_welcome_credits(user)
            except WalletError:
                # Incomplete identity / account or already-awarded document.
                return
            except Exception:
                logger.exception("Falha na atribuição do bónus NKATA; reconciliar.")
    transaction.on_commit(grant)


@receiver(post_save, sender=PedidoEntrada)
def welcome_pedido(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    if settings.NKATA_CREDIT_TRANSITION_ENABLED and instance.documento_confirmado:
        _after_commit(PerfilNKATA.objects.filter(pedido=instance).values_list("usuario_id", flat=True).first())


@receiver(post_save, sender=VerificacaoIdentidadeNKATA)
def welcome_verification(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    if settings.NKATA_CREDIT_TRANSITION_ENABLED and instance.pedido_id and instance.status == "APROVADA":
        _after_commit(PerfilNKATA.objects.filter(pedido_id=instance.pedido_id).values_list("usuario_id", flat=True).first())


@receiver(post_save, sender=PerfilNKATA)
def welcome_profile(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    if settings.NKATA_CREDIT_TRANSITION_ENABLED and instance.status == "ATIVO":
        _after_commit(instance.usuario_id)


@receiver(post_save, sender=get_user_model())
def welcome_account(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return
    if settings.NKATA_CREDIT_TRANSITION_ENABLED and instance.is_active and not instance.is_staff and not instance.is_superuser:
        _after_commit(instance.pk)
