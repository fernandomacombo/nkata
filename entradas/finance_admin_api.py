"""Read-only financial administration. Never return provider secrets or media."""
from django.conf import settings
from django.db.models import BigIntegerField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .credit_catalog import credit_catalog
from .models import CarteiraNKATA, MovimentoCreditoNKATA, PedidoPagamentoNKATA
from .user_roles import has_admin_capability
from .payment_service import payments_enabled
from .wallet_service import credit_spending_enabled

SECTIONS = ("overview", "wallets", "payments", "movements", "consumption", "bonuses", "catalogue", "audit")
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
    ledger = MovimentoCreditoNKATA.objects.all()
    return {
        "wallet_count": CarteiraNKATA.objects.count(),
        "total_balance": _sum(CarteiraNKATA.objects.all(), "saldo"),
        "settled_revenue_mzn": f'{_sum(settled, "valor"):.2f}',
        "settled_count": settled.count(),
        "pending_count": orders.filter(estado__in=["CRIADO", "PENDENTE", "INCERTO", "REVISAO"]).count(),
        "review_count": orders.filter(estado="REVISAO").count(),
        "recharge_credits": _sum(ledger.filter(tipo="RECARGA"), "quantidade"),
        "consumed_credits": -_sum(ledger.filter(tipo="CONSUMO"), "quantidade"),
        "bonus_credits": _sum(ledger.filter(tipo="BONUS"), "quantidade"),
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
            "reference": order.referencia, "created_at": order.criado_em,
            "confirmed_at": order.confirmado_em, "fulfilled_at": order.aplicado_em}


def _catalogue():
    return {"catalogue": credit_catalog(purchase_enabled=False),
            "checkout_configured": bool(payments_enabled() and settings.NKATA_CREDIT_CHECKOUT_ENABLED),
            "spending_enabled": credit_spending_enabled(),
            "call_billing_enabled": False}


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
            rows = rows.filter(tipo="BONUS")
        if q:
            rows = rows.filter(Q(carteira__usuario__username__icontains=q) | Q(carteira__usuario__email__icontains=q)
                | Q(carteira__usuario__first_name__icontains=q) | Q(referencia__icontains=q) | Q(motivo__icontains=q))
        serialize = _movement_row
    response = Response({"total": rows.count(), "offset": offset, "limit": PAGE_SIZE,
                         "results": [serialize(row) for row in rows[offset:offset+PAGE_SIZE]]})
    response["Cache-Control"] = "private, no-store"
    return response
