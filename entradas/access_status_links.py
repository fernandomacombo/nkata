from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import urlencode

from .models import PedidoEntrada


_STATUS_LINK_SALT = "nkata.access-status-link.v1"


def _fingerprint(pedido):
    return salted_hmac(_STATUS_LINK_SALT, f"{pedido.token}:{pedido.email}").hexdigest()


def access_status_link(pedido):
    proof = signing.dumps([pedido.pk, _fingerprint(pedido)], salt=_STATUS_LINK_SALT)
    fragment = urlencode({"consulta": proof})
    return f"{settings.NKATA_FRONTEND_URL.rstrip('/')}/acompanhar-pedido/#{fragment}"


def request_from_status_link(proof):
    try:
        pk, fingerprint = signing.loads(proof, salt=_STATUS_LINK_SALT, max_age=timedelta(hours=48))
    except (signing.BadSignature, TypeError, ValueError):
        return None
    pedido = PedidoEntrada.objects.filter(pk=pk).first()
    if pedido and constant_time_compare(fingerprint, _fingerprint(pedido)):
        return pedido
    return None
