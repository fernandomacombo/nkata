"""Remove the abandoned launch conversion from isolated staging only."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from entradas.models import MovimentoCreditoNKATA, PedidoPagamentoNKATA
from entradas.wallet_service import record_movement, credit_balance, WalletError

STAGING_ID = "36306a53-86bc-4a07-9b09-7c42c58f2e43"
KEY = "adjust:launch-cancelled:v1"


def staging_allowed():
    return (settings.NKATA_RAILWAY_ENVIRONMENT_ID == STAGING_ID and
            settings.NKATA_CREDIT_ONLY_ENABLED and settings.NKATA_PAYMENT_SIMULATION_ENABLED
            and not settings.NKATA_PAYMENTS_ENABLED
            and settings.EMAIL_BACKEND == "django.core.mail.backends.dummy.EmailBackend")


@transaction.atomic
def regularize(user_id, apply):
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    rows = MovimentoCreditoNKATA.objects.filter(carteira__usuario=user)
    original = rows.filter(chave="welcome:launch:v1").first()
    if not original or original.tipo != "BONUS" or original.quantidade != 45:
        return "review"
    prior = rows.filter(chave=KEY).first()
    if prior:
        return "existing" if (prior.tipo, prior.quantidade, prior.referencia) == ("AJUSTE",-45,f"bonus:{original.pk}") else "review"
    # Never reclaim real purchases or create debt. Ambiguous cases need review.
    if (PedidoPagamentoNKATA.objects.filter(usuario=user, simulado=False).filter(
            Q(confirmado_em__isnull=False) | Q(aplicado_em__isnull=False) | Q(estado="PAGO")).exists()
            or rows.filter(chave__startswith="paysuite:").exists()
            or credit_balance(user)<45):
        return "review"
    if apply:
        record_movement(user,key=KEY,kind="AJUSTE",amount=-45,reference=f"bonus:{original.pk}",
                        reason="Regularização de bónus promocional de teste")
        return "applied"
    return "eligible"


class Command(BaseCommand):
    help = "Regulariza somente os 45 créditos promocionais de teste. Sem alterações por omissão."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        if not staging_allowed():
            raise CommandError("Regularização reservada ao staging isolado.")
        counts = {"eligible":0,"existing":0,"applied":0,"review":0}
        ids = MovimentoCreditoNKATA.objects.filter(chave="welcome:launch:v1").values_list("carteira__usuario_id",flat=True)
        for user_id in ids.iterator(chunk_size=200):
            try:
                result = regularize(user_id, options["apply"])
            except WalletError:
                result = "review"
            counts[result] += 1
        self.stdout.write("Regularização de bónus de teste: " + "; ".join(f"{k}={v}" for k,v in counts.items()))
