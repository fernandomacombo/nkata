import base64
import hashlib
import hmac
import time

from django.conf import settings


def turn_is_configured():
    turn_urls = list(getattr(settings, "NKATA_WEBRTC_TURN_URLS", []) or [])
    if not turn_urls:
        return False

    shared_secret = str(
        getattr(settings, "NKATA_WEBRTC_TURN_SHARED_SECRET", "") or ""
    ).strip()
    static_username = str(
        getattr(settings, "NKATA_WEBRTC_TURN_USERNAME", "") or ""
    ).strip()
    static_credential = str(
        getattr(settings, "NKATA_WEBRTC_TURN_CREDENTIAL", "") or ""
    ).strip()
    return bool(shared_secret or (static_username and static_credential))


def _temporary_turn_credentials(user):
    secret = str(
        getattr(settings, "NKATA_WEBRTC_TURN_SHARED_SECRET", "") or ""
    ).strip()
    if not secret:
        return None

    ttl = max(
        300,
        min(
            int(getattr(settings, "NKATA_WEBRTC_TURN_CREDENTIAL_TTL", 3600)),
            86400,
        ),
    )
    expires_at = int(time.time()) + ttl
    user_id = getattr(user, "pk", None) or "member"
    username = f"{expires_at}:{user_id}"
    digest = hmac.new(
        secret.encode("utf-8"),
        username.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return username, base64.b64encode(digest).decode("ascii")


def ice_servers_for_user(user):
    servers = []
    stun_urls = list(getattr(settings, "NKATA_WEBRTC_STUN_URLS", []) or [])
    if stun_urls:
        servers.append({"urls": stun_urls})

    turn_urls = list(getattr(settings, "NKATA_WEBRTC_TURN_URLS", []) or [])
    if not turn_urls:
        return servers

    credentials = _temporary_turn_credentials(user)
    if credentials is None:
        username = str(
            getattr(settings, "NKATA_WEBRTC_TURN_USERNAME", "") or ""
        ).strip()
        credential = str(
            getattr(settings, "NKATA_WEBRTC_TURN_CREDENTIAL", "") or ""
        ).strip()
        credentials = (username, credential) if username and credential else None

    if credentials:
        username, credential = credentials
        servers.append({
            "urls": turn_urls,
            "username": username,
            "credential": credential,
        })
    return servers
