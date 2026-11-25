"""Read-only financial administration. Never return provider secrets or media."""
from django.conf import settings
from django.db.models import BigIntegerField, F, Q, Sum, Value, OuterRef, Subquery, CharField
from django.db.models.functions import Cast, Concat
from django.utils import timezone
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .credit_catalog import credit_catalog
from .models import CarteiraNKATA, MovimentoCreditoNKATA, PedidoPagamentoNKATA, ChamadaConversaCreditoNKATA
from .user_roles import has_admin_capability
from .payment_service import payments_enabled
from .wallet_service import credit_spending_enabled

SECTIONS = ("overview", "wallets", "payments", "movements", "consumption", "bonuses", "catalogue", "audit", "calls")
PAGE_SIZE = 50


def _sum(rows, field):
    return rows.aggregate(total=Sum(field))["total"] or 0


def _wallets():
    return CarteiraNKATA.objects.select_related("usuario").annotate(
        ledger_total=Coalesce(Sum("movimentos__quantidade"), Value(0), output_field=BigIntegerField()))


def _credit_orders():
    return PedidoPagamentoNKATA.objects.filter(produto__startswith="CREDITOS_")


def _overview():
    orders = _credit_orders()
    settled = orders.filter(estado="PAGO", aplicado_em__isnull=False, confirmado_em__isnull=False)
    real = settled.filter(simulado=False)
    ledger = MovimentoCreditoNKATA.objects.all()
    return {
        "wallet_count": CarteiraNKATA.objects.count(),
        "total_balance": _sum(CarteiraNKATA.objects.all(), "saldo"),
        "settled_revenue_mzn": f'{_sum(real, "valor"):.2f}',
        "settled_count": real.count(),
        "simulated_count": settled.filter(simulado=True).count(),
        "pending_count": orders.filter(estado__in=["CRIADO", "PENDENTE", "INCERTO", "REVISAO"]).count(),
        "review_count": orders.filter(estado="REVISAO").count(),
        "recharge_credits": _sum(ledger.filter(tipo="RECARGA"), "quantidade"),
        "consumed_credits": -_sum(ledger.filter(tipo="CONSUMO"), "quantidade"),
        "bonus_credits": _sum(ledger.filter(Q(tipo="BONUS") | Q(tipo="AJUSTE", chave="adjust:launch-cancelled:v1")), "quantidade"),
        "inconsistent_wallets": _wallets().exclude(saldo=F("ledger_total")).count(),
    }


def _member(user):
    return {"user_id": user.pk, "name": user.get_full_name() or user.get_username(), "email": user.email}


def _wallet_row(wallet):
    return {"id": wallet.pk, **_member(wallet.usuario), "balance": wallet.saldo,
            "ledger_total": wallet.ledger_total, "consistent": wallet.saldo == wallet.ledger_total,
            "updated_at": wallet.atualizada_em}


def _movement_row(move):
    return {"id": move.pk, **_member(move.carteira.usuario), "kind": move.tipo,
            "amount": move.quantidade, "balance_after": move.saldo_apos,
            "reference": move.referencia, "reason": move.motivo, "created_at": move.criado_em}


def _payment_row(order):
    return {"id": str(order.pk), **_member(order.usuario), "product": order.produto,
            "amount_mzn": str(order.valor), "credits": order.creditos, "status": order.estado,
            "reference": order.referencia, "simulated": order.simulado, "created_at": order.criado_em,
            "confirmed_at": order.confirmado_em, "fulfilled_at": order.aplicado_em}


def _call_rows():
    # Match immutable movements by the native call key prefix and exact payer.
    # UUID casts on SQLite are unhyphenated; compare through normalized reference.
    from django.db.models.functions import Replace
    call_ref = Concat(Value("call:"), Replace(Cast(OuterRef("pk"), CharField()), Value("-"), Value("")))
    ledger = MovimentoCreditoNKATA.objects.annotate(
        normalized_ref=Replace(F("referencia"), Value("-"), Value(""))
    ).filter(carteira__usuario_id=OuterRef("iniciador_id"), normalized_ref=call_ref,
             chave__startswith="call:native:")
    def total(kind):
        return Coalesce(Subquery(ledger.filter(tipo=kind).order_by().values("carteira_id")
            .annotate(total=Sum("quantidade")).values("total")[:1], output_field=BigIntegerField()),
            Value(0), output_field=BigIntegerField())
    return ChamadaConversaCreditoNKATA.objects.select_related("iniciador", "destinatario").annotate(
        debit_total=-total("CONSUMO"), refund_total=total("ESTORNO")
    )


def _call_row(call):
    expected = call.minutos_pagos * call.custo_minuto
    expired = call.expira_em <= timezone.now() and call.estado in ("CHAMANDO", "ACEITE", "ATIVA")
    inconsistent = call.debit_total != expected or not 0 <= call.refund_total <= call.debit_total
    review = "DIVERGENCIA" if inconsistent else "EXPIRADA_SEM_FECHO" if expired else (
        "ESTORNO" if call.refund_total else "SEM_ALERTA")
    return {"id": str(call.pk), "name": call.iniciador.get_full_name() or call.iniciador.get_username(),
            "recipient": call.destinatario.get_full_name() or call.destinatario.get_username(),
            "kind": call.tipo, "status": call.estado, "rate": call.custo_minuto,
            "paid_minutes": call.minutos_pagos, "debited": call.debit_total,
            "refunded": call.refund_total, "net": call.debit_total - call.refund_total,
            "review": review, "created_at": call.criada_em, "expires_at": call.expira_em}


def _catalogue():
    return {"catalogue": credit_catalog(purchase_enabled=False),
            "checkout_configured": bool(payments_enabled() and settings.NKATA_CREDIT_CHECKOUT_ENABLED),
            "spending_enabled": credit_spending_enabled(),
            "call_billing_enabled": False,
            "credit_transition_enabled": settings.NKATA_CREDIT_TRANSITION_ENABLED}


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def finance(request):
    if not request.user.is_active or not has_admin_capability(request.user, "finance"):
        return Response({"detail": "Sem permissão financeira."}, status=403)
    section = request.query_params.get("section", "overview")
    if section not in SECTIONS:
        return Response({"detail": "Área financeira inválida."}, status=400)
    if section == "overview":
        response = Response({"metrics": _overview(), **_catalogue()})
        response["Cache-Control"] = "private, no-store"
        return response
    if section == "catalogue":
        response = Response(_catalogue())
        response["Cache-Control"] = "private, no-store"
        return response
    q = request.query_params.get("q", "").strip()[:120]
    status = request.query_params.get("status", "")
    try:
        offset = int(request.query_params.get("offset", "0"))
        if not 0 <= offset <= 1000000:
            raise ValueError
    except (ValueError, TypeError):
        return Response({"detail": "Paginação inválida."}, status=400)
    if section in ("wallets", "audit"):
        rows = _wallets()
        if section == "audit":
            rows = rows.exclude(saldo=F("ledger_total"))
        if q:
            rows = rows.filter(Q(usuario__username__icontains=q) | Q(usuario__email__icontains=q)
                | Q(usuario__first_name__icontains=q) | Q(usuario__last_name__icontains=q))
        rows = rows.order_by("-atualizada_em", "-pk")
        serialize = _wallet_row
    elif section == "calls":
        rows = _call_rows().order_by("-criada_em", "-pk")
        if status == "REVISAO":
            rows = rows.filter(
                ~Q(debit_total=F("minutos_pagos") * F("custo_minuto")) |
                Q(refund_total__gt=F("debit_total")) |
                Q(refund_total__lt=0) |
                Q(estado__in=["CHAMANDO", "ACEITE", "ATIVA"], expira_em__lte=timezone.now()))
        elif status:
            if status not in {"CHAMANDO", "ACEITE", "ATIVA", "TERMINADA", "RECUSADA", "EXPIRADA"}:
                return Response({"detail": "Estado inválido."}, status=400)
            rows = rows.filter(estado=status)
        if q:
            rows = rows.filter(Q(iniciador__username__icontains=q) | Q(destinatario__username__icontains=q)
                | Q(iniciador__first_name__icontains=q) | Q(destinatario__first_name__icontains=q)
                | Q(iniciador__last_name__icontains=q) | Q(destinatario__last_name__icontains=q)
                | Q(pk__icontains=q))
        serialize = _call_row
    elif section == "payments":
        rows = _credit_orders().select_related("usuario").order_by("-criado_em", "-pk")
        if status:
            if status not in {"CRIADO", "PENDENTE", "INCERTO", "REVISAO", "PAGO", "FALHOU"}:
                return Response({"detail": "Estado inválido."}, status=400)
            rows = rows.filter(estado=status)
        if q:
            rows = rows.filter(Q(usuario__username__icontains=q) | Q(usuario__email__icontains=q)
                | Q(usuario__first_name__icontains=q) | Q(referencia__icontains=q))
        serialize = _payment_row
    else:
        rows = MovimentoCreditoNKATA.objects.select_related("carteira__usuario").order_by("-pk")
        if section == "consumption":
            rows = rows.filter(tipo="CONSUMO")
        if section == "bonuses":
            rows = rows.filter(Q(tipo="BONUS") | Q(tipo="AJUSTE", chave="adjust:launch-cancelled:v1"))
        if q:
            rows = rows.filter(Q(carteira__usuario__username__icontains=q) | Q(carteira__usuario__email__icontains=q)
                | Q(carteira__usuario__first_name__icontains=q) | Q(referencia__icontains=q) | Q(motivo__icontains=q))
        serialize = _movement_row
    response = Response({"total": rows.count(), "offset": offset, "limit": PAGE_SIZE,
                         "results": [serialize(row) for row in rows[offset:offset+PAGE_SIZE]]})
    response["Cache-Control"] = "private, no-store"
    return response
