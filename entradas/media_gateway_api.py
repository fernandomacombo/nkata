"""Signed server-to-server lease endpoint, experimental and staging-only."""
import hashlib
import hmac
import json
import time
import uuid
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .native_call_service import authorize_gateway_minute
from .wallet_service import WalletError

PATH = "/api/internal/media-gateway/minute/"
STAGING = "36306a53-86bc-4a07-9b09-7c42c58f2e43"


def enabled():
    return (settings.NKATA_MEDIA_GATEWAY_TEST_ENABLED and
            settings.NKATA_RAILWAY_ENVIRONMENT_ID == STAGING and
            settings.NKATA_PAYMENT_SIMULATION_ENABLED and
            not settings.NKATA_PAYMENTS_ENABLED and
            settings.NKATA_CREDIT_ONLY_ENABLED and
            settings.EMAIL_BACKEND == "django.core.mail.backends.dummy.EmailBackend" and
            len(settings.NKATA_MEDIA_GATEWAY_SECRET) >= 32)


def reply(payload,status=200):
    response=JsonResponse(payload,status=status)
    response["Cache-Control"]="no-store"
    return response


@csrf_exempt
@require_POST
def minute(request):
    if not enabled():
        return reply({"authorized":False},404)
    if not request.is_secure():
        return reply({"authorized":False},403)
    stamp=request.headers.get("X-NKATA-Media-Time","")
    nonce=request.headers.get("X-NKATA-Media-Nonce","")
    signature=request.headers.get("X-NKATA-Media-Signature","")
    if not stamp.isascii() or not stamp.isdecimal() or len(stamp)>12 or abs(time.time()-int(stamp))>15:
        return reply({"authorized":False},403)
    try:
        if str(uuid.UUID(nonce))!=nonce or len(signature)!=64 or not signature.isascii():
            return reply({"authorized":False},403)
    except (ValueError,TypeError):
        return reply({"authorized":False},403)
    raw=request.body
    if len(raw)>4096:
        return reply({"authorized":False},400)
    message=f"POST\n{PATH}\n{stamp}\n{nonce}\n".encode()+raw
    expected=hmac.new(settings.NKATA_MEDIA_GATEWAY_SECRET.encode(),message,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature):
        return reply({"authorized":False},403)
    try:
        # Redis must be shared across all web workers in staging.
        if not cache.add(f"media-gateway:nonce:{nonce}",1,timeout=40):
            return reply({"authorized":False},409)
    except Exception:
        return reply({"authorized":False},503)
    try:
        data=json.loads(raw)
        if not isinstance(data,dict) or set(data)!={"session_id","connected_user_ids","expected_minute"}:
            raise ValueError()
        session_id=uuid.UUID(data["session_id"])
        ids=data["connected_user_ids"]
        index=data["expected_minute"]
        if not isinstance(ids,list) or len(ids)!=2 or len(set(ids))!=2 or any(type(v) is not int or v<=0 for v in ids) or type(index) is not int or not 1<=index<=120:
            raise ValueError()
    except (TypeError,ValueError,AttributeError,UnicodeError):
        return reply({"authorized":False},400)
    try:
        deadline=authorize_gateway_minute(session_id,connected_user_ids=ids,expected_minute=index)
    except WalletError:
        return reply({"authorized":False},409)
    if not deadline:
        return reply({"authorized":False},409)
    return reply({"authorized":True,"minute":index,"paid_until":deadline.isoformat()})
