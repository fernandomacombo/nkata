import hashlib
import hmac
import json

from django.conf import settings
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .models import PedidoPagamentoNKATA
from .payment_service import PaymentError, reconcile, serialize_order, start_checkout


class PaymentThrottle(UserRateThrottle):
    rate = "12/min"
    scope = "nkata_payment"


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PaymentThrottle])
def api_payments(request):
    if request.method == "GET":
        return Response({"results": [serialize_order(o) for o in
            PedidoPagamentoNKATA.objects.filter(usuario=request.user).order_by("-criado_em")[:20]]})
    if not isinstance(request.data, dict) or set(request.data) - {"product", "key"}:
        return Response({"detail": "Envie apenas o pacote e a chave do pedido."}, status=400)
    product = request.data.get("product")
    if not isinstance(product, str):
        return Response({"detail": "Pacote inválido."}, status=400)
    try:
        order = start_checkout(request.user, product, request.data.get("key"))
        return Response(serialize_order(order))
    except PaymentError as error:
        return Response({"detail": str(error)}, status=error.status)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([PaymentThrottle])
def api_payment_check(request, payment_id):
    order = PedidoPagamentoNKATA.objects.filter(pk=payment_id, usuario=request.user).first()
    if not order:
        return Response({"detail": "Pagamento não encontrado."}, status=404)
    try:
        return Response(serialize_order(reconcile(order)))
    except PaymentError as error:
        return Response({"detail": str(error)}, status=error.status)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([])
def api_paysuite_webhook(request):
    secret = settings.NKATA_PAYSUITE_WEBHOOK_SECRET
    if not secret:
        return Response(status=503)
    raw = request.body
    if len(raw) > 16384:
        return Response(status=413)
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Webhook-Signature", "")):
        return Response(status=403)
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            return Response(status=400)
    except (ValueError, UnicodeDecodeError):
        return Response(status=400)
    if payload.get("event") not in ("payment.success", "payment.failed"):
        return Response(status=200)
    data = payload["data"]
    if not isinstance(data.get("reference"), str) or not isinstance(data.get("id"), str):
        return Response(status=400)
    order = PedidoPagamentoNKATA.objects.filter(referencia=data["reference"]).first()
    if not order:
        return Response(status=200)  # Other products may share the merchant account.
    if not order.provedor_id:
        return Response(status=503)  # Creation is still being saved; ask for retry.
    if data["id"] != order.provedor_id:
        return Response(status=409)
    try:
        reconcile(order)  # Fetch authoritative server-to-server details.
    except PaymentError as error:
        return Response(status=error.status)
    return Response(status=200)
