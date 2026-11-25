"""Signed server-to-server lease endpoint, experimental and staging-only."""
import hashlib
import hmac
import json
import time
import uuid
from django.conf import settings
from django.core.cache import cache
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .native_call_service import authorize_gateway_minute, _locked_session, _allowed, reconcile_unstarted_minute
from .wallet_service import credit_spending_enabled
from .wallet_service import WalletError
from .webrtc_credentials import native_ice_servers

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


def authenticate_gateway(request, path):
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
    message=f"POST\n{path}\n{stamp}\n{nonce}\n".encode()+raw
    expected=hmac.new(settings.NKATA_MEDIA_GATEWAY_SECRET.encode(),message,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature):
        return reply({"authorized":False},403)
    try:
        # Redis must be shared across all web workers in staging.
        if not cache.add(f"media-gateway:nonce:{nonce}",1,timeout=40):
            return reply({"authorized":False},409)
    except Exception:
        return reply({"authorized":False},503)
    return None


@csrf_exempt
@require_POST
def minute(request):
    error=authenticate_gateway(request, PATH)
    if error is not None:
        return error
    raw=request.body
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
    # Signed admission is required for each peer, in addition to the SFU's
    # server-owned proof of connection. Cache failure must not permit billing.
    keys=[f"media-gateway:admitted:{session_id}:{uid}" for uid in ids]
    try:
        admitted=cache.get_many(keys)
        if any(admitted.get(key)!=1 for key in keys):
            return reply({"authorized":False},409)
    except Exception:
        return reply({"authorized":False},503)
    try:
        deadline=authorize_gateway_minute(session_id,connected_user_ids=ids,expected_minute=index)
    except WalletError:
        return reply({"authorized":False},409)
    if not deadline:
        return reply({"authorized":False},409)
    return reply({"authorized":True,"minute":index,"paid_until":deadline.isoformat()})

# A ticket is an admission credential, never a credit lease or evidence of RTP.
JOIN_PATH = "/api/internal/media-gateway/join/"
JOIN_SALT = "nkata.media.join.v1"
JOIN_TTL = 30


def _admission(session_id, user_id):
    session, chat, profiles, users = _locked_session(session_id)
    if (session.estado != "ACEITE" or timezone.now() >= session.expira_em
        or not credit_spending_enabled() or not _allowed(chat, profiles, users)
        or {u.pk for u in users} != {session.iniciador_id, session.destinatario_id}
        or user_id not in (session.iniciador_id, session.destinatario_id)):
        raise WalletError("Chamada indisponível.")
    return session


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def issue_join_ticket(request, session_id):
    if not enabled():
        return reply({"authorized": False}, 404)
    if not request.is_secure():
        return reply({"authorized": False}, 403)
    try:
        session = _admission(session_id, request.user.pk)
    except WalletError:
        return reply({"authorized": False}, 404)
    payload = {"sid": str(session.pk), "uid": request.user.pk, "nonce": uuid.uuid4().hex}
    ticket = signing.dumps(payload, key=settings.NKATA_MEDIA_GATEWAY_SECRET, salt=JOIN_SALT)
    return reply({"ticket": ticket, "expires_in": JOIN_TTL})


@csrf_exempt
@require_POST
@transaction.atomic
def redeem_join_ticket(request):
    error = authenticate_gateway(request, JOIN_PATH)
    if error is not None:
        return error
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or set(data) != {"ticket"}:
            raise ValueError()
        token = data["ticket"]
        if not isinstance(token, str) or len(token) > 2048:
            raise ValueError()
        payload = signing.loads(token, key=settings.NKATA_MEDIA_GATEWAY_SECRET,
                                salt=JOIN_SALT, max_age=JOIN_TTL, fallback_keys=[])
        if not isinstance(payload, dict) or set(payload) != {"sid", "uid", "nonce"}:
            raise ValueError()
        sid = uuid.UUID(payload["sid"])
        uid = payload["uid"]
        if type(uid) is not int or uid <= 0:
            raise ValueError()
        if uuid.UUID(hex=payload["nonce"]).hex != payload["nonce"]:
            raise ValueError()
        session = _admission(sid, uid)
    except (ValueError, TypeError, AttributeError, UnicodeError, signing.BadSignature, WalletError):
        return reply({"authorized": False}, 403)
    try:
        # One admission per participant per call. Reconnection is intentionally
        # unsupported until a server-owned transport lifecycle is implemented.
        if not cache.add(f"media-gateway:admitted:{sid}:{uid}", 1, timeout=7500):
            return reply({"authorized": False}, 409)
    except Exception:
        return reply({"authorized": False}, 503)
    return reply({"authorized": True, "session_id": str(sid), "user_id": uid,
                  "kind": session.tipo})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def call_ice_config(request, session_id):
    if not enabled():
        return reply({"authorized": False}, 404)
    if not request.is_secure():
        return reply({"authorized": False}, 403)
    try:
        session = _admission(session_id, request.user.pk)
    except WalletError:
        return reply({"authorized": False}, 404)
    config = native_ice_servers(session, request.user)
    if config is None:
        return reply({"authorized": False, "detail": "Media relay unavailable."}, 503)
    return reply(config)


RECONCILE_PATH = "/api/internal/media-gateway/reconcile/"


@csrf_exempt
@require_POST
def reconcile(request):
    error = authenticate_gateway(request, RECONCILE_PATH)
    if error is not None:
        return error
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or set(data) != {"session_id", "user_ids", "minute", "outcome"}:
            raise ValueError()
        sid = uuid.UUID(data["session_id"])
        ids, minute = data["user_ids"], data["minute"]
        if (not isinstance(ids, list) or len(ids) != 2
                or any(type(uid) is not int or uid <= 0 for uid in ids)
                or len(set(ids)) != 2 or type(minute) is not int or not 1 <= minute <= 120
                or data["outcome"] != "RESUME_NOT_ATTEMPTED"):
            raise ValueError()
    except (ValueError, TypeError, AttributeError, UnicodeError):
        return reply({"reconciled": False}, 400)
    try:
        result = reconcile_unstarted_minute(sid, user_ids=ids, minute=minute)
    except WalletError:
        return reply({"reconciled": False}, 409)
    return reply({"reconciled": True, **result})
