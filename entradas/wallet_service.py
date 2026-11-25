"""Internal ledger. No public mutation endpoints until commercial rollout."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum

from .credit_catalog import WELCOME_CREDITS
from .identity_models import pedido_tem_identidade_verificada
from .models import CarteiraNKATA, MovimentoCreditoNKATA, PerfilNKATA


class WalletError(ValueError):
    pass


@transaction.atomic
def record_movement(user, *, key, kind, amount, reference, reason):
    """Serialize each user's writes. Exact retries return the original movement."""
    if type(amount) is not int or amount == 0 or abs(amount) > 10**9:
        raise WalletError("Quantidade de créditos inválida.")
    if kind not in {"BONUS", "RECARGA", "CONSUMO", "ESTORNO", "AJUSTE"}:
        raise WalletError("Tipo de movimento inválido.")
    if (kind == "CONSUMO" and amount > 0) or (kind in {"BONUS", "RECARGA", "ESTORNO"} and amount < 0):
        raise WalletError("Sinal da quantidade inválido.")
    for value, limit in ((key, 120), (reference, 120), (reason, 240)):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise WalletError("Identificação ou motivo inválido.")
    locked_user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if locked_user.is_staff or locked_user.is_superuser:
        raise WalletError("Uma conta administrativa não possui carteira de membro.")
    wallet, _ = CarteiraNKATA.objects.get_or_create(usuario=locked_user)
    wallet = CarteiraNKATA.objects.select_for_update().get(pk=wallet.pk)
    previous = wallet.movimentos.filter(chave=key).first()
    if previous:
        if (previous.tipo, previous.quantidade, previous.referencia, previous.motivo) != (kind, amount, reference, reason):
            raise WalletError("Chave já utilizada com dados diferentes.")
        return previous
    if wallet.saldo + amount < 0:
        raise WalletError("Saldo insuficiente.")
    if wallet.saldo + amount > 10**12:
        raise WalletError("Limite de saldo atingido.")
    movement = MovimentoCreditoNKATA.objects.create(carteira=wallet, chave=key,
        tipo=kind, quantidade=amount, saldo_apos=wallet.saldo+amount,
        referencia=reference, motivo=reason)
    wallet.saldo = movement.saldo_apos
    wallet.save(update_fields=["saldo", "atualizada_em"])
    return movement


@transaction.atomic
def grant_welcome_credits(user):
    # Do not grant to unverified profiles or legacy approvals without an actual
    # identity record. This function is deliberately not hooked into production yet.
    locked = get_user_model().objects.select_for_update().get(pk=user.pk)
    profile = PerfilNKATA.objects.filter(usuario=locked, status="ATIVO").select_related("pedido", "pedido__verificacao_identidade").first()
    verification = getattr(profile.pedido, "verificacao_identidade", None) if profile else None
    if (not locked.is_active or not profile or not verification or verification.status != "APROVADA"
            or not profile.pedido.documento_confirmado or not pedido_tem_identidade_verificada(profile.pedido)):
        raise WalletError("Verificação de identidade obrigatória.")
    return record_movement(locked, key="welcome:v1", kind="BONUS", amount=WELCOME_CREDITS,
                           reference="welcome:v1", reason="Bónus de boas-vindas após verificação")


def wallet_snapshot(user):
    wallet = CarteiraNKATA.objects.filter(usuario=user).first()
    if not wallet:
        return {"saldo": 0, "movimentos": []}
    # The ledger tail contains its own balance; use it for a coherent read
    # even if another request credits the wallet between the two queries.
    movements = list(wallet.movimentos.all()[:30])
    return {"saldo": movements[0].saldo_apos if movements else wallet.saldo,
            "movimentos": [{"id": m.pk, "tipo": m.tipo, "quantidade": m.quantidade,
                            "saldo_apos": m.saldo_apos, "motivo": m.motivo,
                            "criado_em": m.criado_em} for m in movements]}


def reconcile_balance(wallet):
    """Audit only; never silently adjust a financial record."""
    wallet.refresh_from_db()
    total = wallet.movimentos.aggregate(total=Sum("quantidade"))["total"] or 0
    return {"saldo": wallet.saldo, "total_movimentos": total, "consistente": wallet.saldo == total}
