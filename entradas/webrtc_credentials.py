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


def native_ice_servers(session, user):
    """Only for a previously authorized native call, never static credentials."""
    secret = str(getattr(settings, "NKATA_WEBRTC_TURN_SHARED_SECRET", "") or "").strip()
    urls = list(getattr(settings, "NKATA_WEBRTC_TURN_URLS", []) or [])
    if (len(secret) < 32 or secret == settings.NKATA_MEDIA_GATEWAY_SECRET or not urls
            or any(not isinstance(url, str) or not url.startswith(("turn:", "turns:")) for url in urls)
            or not any(url.startswith("turns:") for url in urls)):
        return None
    # Covers the agreed maximum call duration plus setup and refresh margin.
    ttl = min(120, session.max_minutos) * 60 + 300
    expires_at = int(time.time()) + ttl
    username = f"{expires_at}:{session.pk}:{user.pk}"
    digest = hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()
    servers = []
    stun = list(getattr(settings, "NKATA_WEBRTC_STUN_URLS", []) or [])
    if stun:
        servers.append({"urls": stun})
    servers.append({"urls": urls, "username": username,
                    "credential": base64.b64encode(digest).decode("ascii")})
    return {"ice_servers": servers, "expires_at": expires_at}
