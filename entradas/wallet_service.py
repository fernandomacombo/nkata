"""Internal ledger. No public mutation endpoints until commercial rollout."""
from datetime import timedelta
import uuid
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.db.models import Sum

from .credit_catalog import WELCOME_CREDITS, CHAT_24H_CREDITS, LAUNCH_CONVERSION_CREDITS
from .identity_models import pedido_tem_identidade_verificada
from .legacy_commercial import convertible_quinzenal
from .models import CarteiraNKATA, MovimentoCreditoNKATA, PerfilNKATA, AcessoChatCreditoNKATA, BonusIdentidadeCreditoNKATA, AcessoPlanoNKATA


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
    # A discrepancy must be investigated, never absorbed into a new debit.
    total = wallet.movimentos.aggregate(total=Sum("quantidade"))["total"] or 0
    tail = wallet.movimentos.values_list("saldo_apos", flat=True).first()
    if wallet.saldo != total or wallet.saldo != (tail if tail is not None else 0):
        raise WalletError("Carteira em revisão. Contacte a equipa NKATA.")
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


def welcome_eligible(profile):
    if not profile or profile.status != "ATIVO" or not profile.usuario_id:
        return False
    user, pedido = profile.usuario, profile.pedido
    verification = getattr(pedido, "verificacao_identidade", None)
    return bool(user.is_active and not user.is_staff and not user.is_superuser and user.has_usable_password()
                and pedido.status == "APROVADO" and pedido.documento_chave and pedido.documento_confirmado
                and verification and verification.status == "APROVADA" and pedido_tem_identidade_verificada(pedido))


@transaction.atomic
def grant_welcome_credits(user):
    # Keep the account and the document as independent idempotency boundaries.
    locked = get_user_model().objects.select_for_update().get(pk=user.pk)
    profile = PerfilNKATA.objects.filter(usuario=locked).select_related("usuario", "pedido", "pedido__verificacao_identidade").first()
    if not welcome_eligible(profile):
        raise WalletError("Verificação de identidade obrigatória.")
    prior = MovimentoCreditoNKATA.objects.filter(carteira__usuario=locked, chave="welcome:v1").first()
    if not prior:
        if BonusIdentidadeCreditoNKATA.objects.filter(documento_chave=profile.pedido.documento_chave).exists():
            raise WalletError("Esta identidade já recebeu o bónus de boas-vindas.")
        try:
            with transaction.atomic():
                prior = record_movement(locked, key="welcome:v1", kind="BONUS", amount=WELCOME_CREDITS,
                                           reference="welcome:v1", reason="Bónus de boas-vindas após verificação")
                BonusIdentidadeCreditoNKATA.objects.create(documento_chave=profile.pedido.documento_chave, movimento=prior)
        except IntegrityError:
            raise WalletError("Não foi possível atribuir o bónus; requer revisão.") from None
    if settings.NKATA_CREDIT_TRANSITION_ENABLED:
        # Only explicitly promotional grants qualify, even if the promotion expired.
        # Preserve the entitlement row for audit, but retire its benefits atomically.
        access = convertible_quinzenal(locked.pk).select_for_update().first()
        if access:
            if not BonusIdentidadeCreditoNKATA.objects.filter(movimento=prior, documento_chave=profile.pedido.documento_chave).exists():
                raise WalletError("A origem do bónus precisa de revisão.")
            record_movement(locked, key="welcome:launch:v1", kind="BONUS",
                amount=LAUNCH_CONVERSION_CREDITS-WELCOME_CREDITS, reference=f"promo:{access.pk}",
                reason="Conversão do bónus Quinzenal de lançamento")
            access.origem = "PROMO_CONVERTIDA"
            access.save(update_fields=["origem", "atualizado_em"])
    return prior


def welcome_status(user):
    profile = PerfilNKATA.objects.filter(usuario=user).select_related("usuario", "pedido", "pedido__verificacao_identidade").first()
    promotional = convertible_quinzenal(user.pk).exists()
    granted = MovimentoCreditoNKATA.objects.filter(carteira__usuario=user, chave="welcome:v1").exists()
    converted = MovimentoCreditoNKATA.objects.filter(carteira__usuario=user, chave="welcome:launch:v1").exists()
    eligible = welcome_eligible(profile)
    return {"enabled": settings.NKATA_CREDIT_TRANSITION_ENABLED, "eligible": eligible,
            "claimable": settings.NKATA_CREDIT_TRANSITION_ENABLED and eligible and (not granted or promotional),
            "granted": granted, "converted": converted,
            "credits": LAUNCH_CONVERSION_CREDITS if promotional or converted else WELCOME_CREDITS}


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


def credit_spending_enabled():
    return bool(settings.NKATA_CREDIT_SPENDING_ENABLED)


def active_chat_credit_access(user):
    now = timezone.now()
    return AcessoChatCreditoNKATA.objects.filter(
        movimento__carteira__usuario=user, inicio__lte=now, fim__gt=now
    ).order_by("-fim").first()


def credit_balance(user):
    return CarteiraNKATA.objects.filter(usuario=user).values_list("saldo", flat=True).first() or 0


@transaction.atomic
def unlock_chat(user, *, key, expected_cost):
    from .plan_service import plan_for_user
    try:
        key = str(uuid.UUID(str(key)))
    except (ValueError, TypeError, AttributeError):
        raise WalletError("Chave de operação inválida.") from None
    locked = get_user_model().objects.select_for_update().get(pk=user.pk)
    profile = PerfilNKATA.objects.filter(usuario=locked, status="ATIVO").select_related("pedido").first()
    if (not locked.is_active or locked.is_staff or locked.is_superuser or not profile
            or not pedido_tem_identidade_verificada(profile.pedido)):
        raise WalletError("Identidade verificada obrigatória.")
    previous = AcessoChatCreditoNKATA.objects.filter(movimento__carteira__usuario=locked, movimento__chave=f"chat24:{key}").first()
    if previous:
        return previous, False
    active = active_chat_credit_access(locked)
    if active:
        return active, False
    if plan_for_user(locked)["features"]["chat_text"]:
        return None, False
    if not credit_spending_enabled():
        raise WalletError("O consumo de créditos ainda não está disponível.")
    if type(expected_cost) is not int or expected_cost != CHAT_24H_CREDITS:
        raise WalletError("Confirme o preço atual antes de continuar.")
    movement = record_movement(locked, key=f"chat24:{key}", kind="CONSUMO",
        amount=-CHAT_24H_CREDITS, reference="CHAT_24H", reason="Texto livre durante 24 horas")
    now = timezone.now()
    return AcessoChatCreditoNKATA.objects.create(movimento=movement, inicio=now, fim=now+timedelta(hours=24)), True


def chat_credit_snapshot(user, text_enabled):
    access = active_chat_credit_access(user)
    return {"enabled": credit_spending_enabled(), "cost": CHAT_24H_CREDITS,
            "balance": credit_balance(user), "expires_at": access.fim if access else None,
            "can_unlock": credit_spending_enabled() and not text_enabled}
