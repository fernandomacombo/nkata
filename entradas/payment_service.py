"""PaySuite checkout and exactly-once fulfillment; no browser-trusted payment state."""
import re
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import AcessoPlanoNKATA, PedidoPagamentoNKATA
from .credit_catalog import CREDIT_PRODUCTS
from .wallet_service import record_movement, WalletError
from .identity_models import pedido_tem_identidade_verificada
from .user_roles import active_member_profile_for_user
from .plan_service import (
    PLAN_PRICES_MZN, PLAN_DURATIONS, ACTIVE_RECHARGE_PRICES_MZN,
    active_plan_access, grant_recharge,
)

API_URL = "https://paysuite.tech/api/v1/payments"
OPEN_STATES = ["CRIADO", "PENDENTE", "INCERTO", "REVISAO"]


class PaymentError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def payments_enabled():
    return bool(settings.NKATA_PAYMENTS_ENABLED and settings.NKATA_PAYSUITE_TOKEN
                and settings.NKATA_PAYSUITE_WEBHOOK_SECRET and settings.NKATA_PAYMENT_ORIGIN)


def simulation_enabled():
    return bool(settings.NKATA_PAYMENT_SIMULATION_ENABLED
                and settings.NKATA_RAILWAY_ENVIRONMENT_ID == "36306a53-86bc-4a07-9b09-7c42c58f2e43"
                and not settings.NKATA_PAYMENTS_ENABLED and settings.NKATA_CREDIT_TRANSITION_ENABLED
                and settings.EMAIL_BACKEND == "django.core.mail.backends.dummy.EmailBackend")


def credit_checkout_enabled(user):
    profile = active_member_profile_for_user(user)
    return bool((simulation_enabled() or (payments_enabled() and settings.NKATA_CREDIT_CHECKOUT_ENABLED)) and profile
                and pedido_tem_identidade_verificada(profile.pedido))


def provider_request(method, payment_id=None, payload=None):
    if simulation_enabled() or not settings.NKATA_PAYSUITE_TOKEN:
        raise PaymentError("Pagamentos temporariamente indisponíveis.", 503)
    if payment_id is not None and not re.fullmatch(r"[A-Za-z0-9-]{1,64}", payment_id):
        raise PaymentError("Identificador de pagamento inválido.", 502)
    url = API_URL + (f"/{payment_id}" if payment_id else "")
    try:
        response = requests.request(method, url, json=payload,
            headers={"Authorization": f"Bearer {settings.NKATA_PAYSUITE_TOKEN}", "Accept": "application/json"},
            timeout=(2, 3), allow_redirects=False)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or body.get("status") != "success" or not isinstance(body.get("data"), dict):
            raise ValueError("Invalid provider response")
        return body["data"]
    except (requests.RequestException, ValueError):
        # Do not expose provider bodies/tokens or automatically retry a POST.
        raise PaymentError("Não foi possível confirmar o pagamento. Consulte o estado antes de tentar novamente.", 503) from None


def valid_checkout_url(url):
    if not isinstance(url, str) or len(url) > 500:
        return False
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname in settings.NKATA_CHECKOUT_HOSTS
                and not parsed.username and not parsed.password and parsed.port in (None, 443))
    except ValueError:
        return False


def snapshot(product):
    if product in CREDIT_PRODUCTS:
        pack = CREDIT_PRODUCTS[product]
        return Decimal(pack["price_mzn"]), 0, pack["credits"]
    if product in ("ESSENCIAL", "PREMIUM", "QUINZENAL"):
        return Decimal(PLAN_PRICES_MZN[product]), PLAN_DURATIONS[product], 0
    if product == "RECARGA10":
        return Decimal(ACTIVE_RECHARGE_PRICES_MZN[10]), 0, 10
    raise PaymentError("Escolha um pacote NKATA disponível.")


def check_identity(order, data):
    try:
        amount = Decimal(str(data.get("amount")))
    except (InvalidOperation, ValueError):
        raise PaymentError("Montante do prestador inválido.", 409) from None
    # PaySuite documents amounts in MZN and does not always return currency.
    if (not amount.is_finite() or amount != order.valor or data.get("reference") != order.referencia
            or (order.provedor_id and str(data.get("id")) != order.provedor_id)
            or data.get("currency", "MZN") != order.moeda):
        raise PaymentError("Os dados do pagamento precisam de revisão.", 409)


def start_checkout(user, product, key):
    if simulation_enabled():
        return start_simulated_checkout(user, product, key)
    if not payments_enabled():
        raise PaymentError("Pagamentos ainda não disponíveis.", 503)
    try:
        key = uuid.UUID(str(key))
    except (ValueError, TypeError, AttributeError):
        raise PaymentError("Chave do pedido inválida.") from None
    amount, days, credits = snapshot(product)
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=user.pk)
        existing = PedidoPagamentoNKATA.objects.filter(usuario=user, chave=key).first()
        if existing:
            if existing.produto != product or existing.simulado:
                raise PaymentError("Esta chave já pertence a outro pacote.", 409)
            return existing
        if settings.NKATA_CREDIT_TRANSITION_ENABLED and product not in CREDIT_PRODUCTS:
            raise PaymentError("Os antigos planos e recargas deixaram de estar à venda. Consulte a Carteira NKATA.", 403)
        if product in CREDIT_PRODUCTS and not credit_checkout_enabled(user):
            raise PaymentError("A compra de créditos ainda não está disponível para esta conta.", 403)
        profile = getattr(user, "perfil_nkata", None)
        if not user.is_active or user.is_staff or user.is_superuser or not profile or profile.status != "ATIVO":
            raise PaymentError("É necessário um perfil ativo para comprar.", 403)
        if PedidoPagamentoNKATA.objects.filter(usuario=user, estado__in=OPEN_STATES).exists():
            raise PaymentError("Já existe um pagamento por confirmar. Consulte o histórico.", 409)
        access = active_plan_access(user)
        if days and access and access.origem != "PROMO_LANCAMENTO" and access.plano != product:
            raise PaymentError("Pode renovar o plano atual. A troca estará disponível após a validade terminar.", 409)
        order = PedidoPagamentoNKATA.objects.create(usuario=user, chave=key,
            referencia=f"NKATA{uuid.uuid4().hex.upper()}", produto=product, valor=amount, dias=days, creditos=credits)
    origin = settings.NKATA_PAYMENT_ORIGIN
    description = (f"NKATA - {order.creditos} créditos" if product in CREDIT_PRODUCTS else
                   f"NKATA {product} - {days} dias" if days else "NKATA recarga de 10 sinais")
    try:
        data = provider_request("POST", payload={"amount": str(order.valor), "reference": order.referencia,
            "description": description, "return_url": f"{origin}/?nkata_payment={order.id}",
            "webhook_url": f"{origin}/api/pagamentos/paysuite/webhook/"})
        check_identity(order, data)
        provider_id = str(data.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", provider_id):
            raise PaymentError("Resposta do prestador inválida.", 502)
        # Persist the provider ID even if its checkout URL needs investigation.
        order.provedor_id = provider_id
        order.save(update_fields=["provedor_id"])
        if not valid_checkout_url(data.get("checkout_url")):
            raise PaymentError("O endereço de pagamento precisa de revisão.", 502)
        PedidoPagamentoNKATA.objects.filter(pk=order.pk, aplicado_em__isnull=True, confirmado_em__isnull=True).update(
            checkout_url=data["checkout_url"], estado="PENDENTE")
        order.refresh_from_db()
    except PaymentError:
        PedidoPagamentoNKATA.objects.filter(pk=order.pk, aplicado_em__isnull=True).update(estado="INCERTO")
        raise
    return order


def reconcile(order):
    if order.simulado or simulation_enabled():
        raise PaymentError("Pedido indisponível para reconciliação real.", 409)
    if not order.provedor_id:
        raise PaymentError("Pagamento ainda em preparação ou a aguardar revisão.", 409)
    data = provider_request("GET", payment_id=order.provedor_id)
    return _settle_authoritative(order, data, simulated=False)


def _settle_authoritative(order, data, *, simulated):
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=order.usuario_id)
        order = PedidoPagamentoNKATA.objects.select_for_update().get(pk=order.pk)
        if order.simulado != simulated or (simulated and not simulation_enabled()):
            raise PaymentError("Origem do pagamento inválida.", 409)
        check_identity(order, data)
        order.ultima_verificacao = timezone.now()
        # An old failure notification must never undo a confirmed fulfillment.
        if order.aplicado_em:
            order.save(update_fields=["ultima_verificacao"])
            return order
        state = data.get("status")
        if state == "completed":
            transaction_data = data.get("transaction")
            if not isinstance(transaction_data, dict) or transaction_data.get("status") != "completed":
                raise PaymentError("A transação ainda não está confirmada.", 409)
            order.confirmado_em = order.confirmado_em or timezone.now()
            access = active_plan_access(user)
            profile = getattr(user, "perfil_nkata", None)
            if (not user.is_active or not profile or profile.status != "ATIVO"
                    or (order.dias and access and access.origem != "PROMO_LANCAMENTO" and access.plano != order.produto)):
                order.estado = "REVISAO"
            else:
                if order.dias:
                    end = (access.fim if access and access.origem != "PROMO_LANCAMENTO" else timezone.now()) + timedelta(days=order.dias)
                    AcessoPlanoNKATA.objects.update_or_create(usuario=user, defaults={
                        "plano": order.produto, "inicio": timezone.now(), "fim": end, "origem": "PAYSUITE"})
                    order.validade_concedida = end
                elif order.produto in CREDIT_PRODUCTS:
                    # Honor the immutable order snapshot even if future prices change.
                    # Turning off new checkout must not prevent settlement of existing orders.
                    if not order.creditos or user.is_staff or user.is_superuser:
                        order.estado = "REVISAO"
                        order.save()
                        return order
                    try:
                        record_movement(user, key=f"{'simulated' if simulated else 'paysuite'}:{order.pk}", kind="RECARGA",
                                        amount=order.creditos, reference=order.referencia,
                                        reason="Recarga SIMULADA (sem dinheiro real)" if simulated else "Recarga de créditos NKATA")
                    except WalletError:
                        order.estado = "REVISAO"
                        order.save()
                        return order
                else:
                    grant_recharge(user, order.creditos)
                order.aplicado_em = timezone.now()
                order.estado = "PAGO"
        elif state in ("failed", "cancelled"):
            # Keep confirmed-but-unfulfilled funds in review.
            order.estado = "REVISAO" if order.confirmado_em else "FALHOU"
        elif state == "pending":
            order.estado = "REVISAO" if order.confirmado_em else "PENDENTE"
        else:
            raise PaymentError("Estado do prestador não reconhecido; requer revisão.", 409)
        order.save()
        return order


def serialize_order(order):
    return {"id": str(order.pk), "reference": order.referencia, "product": order.produto,
            "amount_mzn": str(order.valor), "currency": order.moeda, "status": order.estado,
            "checkout_url": order.checkout_url if order.estado == "PENDENTE" else None,
            "created_at": order.criado_em, "fulfilled_at": order.aplicado_em,
            "valid_until": order.validade_concedida,
            "wallet_credits": order.creditos if order.produto in CREDIT_PRODUCTS else 0,
            "simulated": order.simulado}


@transaction.atomic
def start_simulated_checkout(user, product, key):
    if not simulation_enabled() or product not in CREDIT_PRODUCTS:
        raise PaymentError("Simulação indisponível.", 403)
    try:
        key = uuid.UUID(str(key))
    except (ValueError, TypeError, AttributeError):
        raise PaymentError("Chave do pedido inválida.") from None
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if not credit_checkout_enabled(user):
        raise PaymentError("Identidade verificada obrigatória.", 403)
    existing = PedidoPagamentoNKATA.objects.filter(usuario=user, chave=key).first()
    if existing:
        if not existing.simulado or existing.produto != product:
            raise PaymentError("Chave já utilizada.", 409)
        return existing
    if PedidoPagamentoNKATA.objects.filter(usuario=user, simulado=True, estado__in=OPEN_STATES).exists():
        raise PaymentError("Já existe uma simulação pendente.", 409)
    amount, days, credits = snapshot(product)
    return PedidoPagamentoNKATA.objects.create(usuario=user, chave=key,
        referencia=f"SIMNKATA{uuid.uuid4().hex.upper()}", produto=product, valor=amount,
        dias=days, creditos=credits, simulado=True, estado="PENDENTE",
        provedor_id=f"SIM-{uuid.uuid4().hex}")


@transaction.atomic
def resolve_simulated_checkout(user, order_id, outcome):
    if not simulation_enabled() or outcome not in ("completed", "failed"):
        raise PaymentError("Simulação indisponível ou resultado inválido.", 403)
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if not credit_checkout_enabled(user):
        raise PaymentError("Identidade verificada obrigatória.", 403)
    order = PedidoPagamentoNKATA.objects.select_for_update().filter(pk=order_id, usuario=user, simulado=True).first()
    if not order:
        raise PaymentError("Simulação não encontrada.", 404)
    if order.estado in ("PAGO", "FALHOU"):
        return order
    if order.estado != "PENDENTE" or order.produto not in CREDIT_PRODUCTS or order.dias:
        raise PaymentError("Simulação em revisão.", 409)
    # The simulator is a trusted server-side fixture only. Never call the
    # actual provider and never accept amounts or credit quantities from the browser.
    data = {"id": order.provedor_id, "reference": order.referencia, "amount": str(order.valor),
            "currency": order.moeda, "status": outcome, "transaction": {"status": outcome}}
    return _settle_authoritative(order, data, simulated=True)
