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
from .plan_service import (
    PLAN_PRICES_MZN, PLAN_DURATION_DAYS, ACTIVE_RECHARGE_PRICES_MZN,
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


def provider_request(method, payment_id=None, payload=None):
    if not settings.NKATA_PAYSUITE_TOKEN:
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
    if product in ("ESSENCIAL", "PREMIUM"):
        return Decimal(PLAN_PRICES_MZN[product]), PLAN_DURATION_DAYS, 0
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
    if not payments_enabled():
        raise PaymentError("Pagamentos ainda não disponíveis.", 503)
    try:
        key = uuid.UUID(str(key))
    except (ValueError, TypeError, AttributeError):
        raise PaymentError("Chave do pedido inválida.") from None
    amount, days, credits = snapshot(product)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        existing = PedidoPagamentoNKATA.objects.filter(usuario=user, chave=key).first()
        if existing:
            if existing.produto != product:
                raise PaymentError("Esta chave já pertence a outro pacote.", 409)
            return existing
        profile = getattr(user, "perfil_nkata", None)
        if not profile or profile.status != "ATIVO":
            raise PaymentError("É necessário um perfil ativo para comprar.", 403)
        if PedidoPagamentoNKATA.objects.filter(usuario=user, estado__in=OPEN_STATES).exists():
            raise PaymentError("Já existe um pagamento por confirmar. Consulte o histórico.", 409)
        access = active_plan_access(user)
        if days and access and access.plano != product:
            raise PaymentError("Pode renovar o plano atual. A troca estará disponível após a validade terminar.", 409)
        order = PedidoPagamentoNKATA.objects.create(usuario=user, chave=key,
            referencia=f"NKATA{uuid.uuid4().hex.upper()}", produto=product, valor=amount, dias=days, creditos=credits)
    origin = settings.NKATA_PAYMENT_ORIGIN
    description = f"NKATA {product} - {days} dias" if days else "NKATA recarga de 10 sinais"
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
    if not order.provedor_id:
        raise PaymentError("Pagamento ainda em preparação ou a aguardar revisão.", 409)
    data = provider_request("GET", payment_id=order.provedor_id)
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=order.usuario_id)
        order = PedidoPagamentoNKATA.objects.select_for_update().get(pk=order.pk)
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
                    or (order.dias and access and access.plano != order.produto)):
                order.estado = "REVISAO"
            else:
                if order.dias:
                    end = (access.fim if access else timezone.now()) + timedelta(days=order.dias)
                    AcessoPlanoNKATA.objects.update_or_create(usuario=user, defaults={
                        "plano": order.produto, "inicio": timezone.now(), "fim": end, "origem": "PAYSUITE"})
                    order.validade_concedida = end
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
            "valid_until": order.validade_concedida}
