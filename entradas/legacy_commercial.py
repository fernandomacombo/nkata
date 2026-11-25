"""Commercial cutover: keep historical evidence, never silently discard real payments."""
from django.conf import settings
from django.db.models import Q
from .models import AcessoPlanoNKATA, PedidoPagamentoNKATA


def credit_only_enabled():
    return bool(settings.NKATA_CREDIT_ONLY_ENABLED)


def legacy_audit():
    orders = PedidoPagamentoNKATA.objects.filter(simulado=False).exclude(produto__startswith="CREDITOS_")
    # A provider failure with evidence of confirmation is still a blocker.
    unresolved = orders.filter(Q(estado__in=["CRIADO","PENDENTE","INCERTO","REVISAO","PAGO"]) |
                               Q(confirmado_em__isnull=False) | Q(aplicado_em__isnull=False))
    # Acknowledge only named owner tests, preserving all payment evidence.
    # A late confirmation without fulfillment, or an order in review, still blocks.
    reviewed = unresolved.filter(referencia__in=settings.NKATA_LEGACY_TEST_ORDER_REFERENCES).filter(
        Q(estado__in=["CRIADO", "PENDENTE", "INCERTO"], confirmado_em__isnull=True, aplicado_em__isnull=True) |
        Q(estado="PAGO", confirmado_em__isnull=False, aplicado_em__isnull=False)
    )
    blockers = unresolved.exclude(pk__in=reviewed.values("pk"))
    paid_entitlements = AcessoPlanoNKATA.objects.filter(origem="PAYSUITE")
    unknown = AcessoPlanoNKATA.objects.exclude(origem__in=["PAYSUITE","ADMINISTRATIVA","PROMO_LANCAMENTO","PROMO_CONVERTIDA"])
    return {"legacy_orders":orders.count(),"legacy_payment_blockers":blockers.count(), "legacy_test_orders_acknowledged":reviewed.count(),
            "paid_entitlements":paid_entitlements.count(),"unknown_entitlements":unknown.count(),
            "administrative_quinzenal":AcessoPlanoNKATA.objects.filter(plano="QUINZENAL",origem="ADMINISTRATIVA").count(),
            "promotional_quinzenal":AcessoPlanoNKATA.objects.filter(plano="QUINZENAL",origem="PROMO_LANCAMENTO").count()}
