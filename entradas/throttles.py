import hashlib

from rest_framework.throttling import SimpleRateThrottle


def _digest(value):
    return hashlib.sha256(str(value or "").strip().lower().encode("utf-8")).hexdigest()[:20]


class _IdentityThrottle(SimpleRateThrottle):
    data_field = None

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        value = request.data.get(self.data_field, "") if self.data_field else ""
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{_digest(value)}",
        }


class LoginRateThrottle(_IdentityThrottle):
    scope = "login"
    data_field = "email"


class PasswordResetRateThrottle(_IdentityThrottle):
    scope = "password_reset"
    data_field = "email"


class AccessRequestRateThrottle(_IdentityThrottle):
    scope = "access_request"
    data_field = "email"


class AccessStatusRateThrottle(_IdentityThrottle):
    scope = "access_status"
    data_field = "email"


class AccessCodeRecoveryRateThrottle(_IdentityThrottle):
    scope = "access_code_recovery"
    data_field = "email"


class IdentitySessionRateThrottle(_IdentityThrottle):
    scope = "identity_session"
    data_field = "email"


class IdentityCaptureRateThrottle(_IdentityThrottle):
    scope = "identity_capture"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        token = view.kwargs.get("token") or ""
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{_digest(token)}",
        }


class IdentityStatusRateThrottle(IdentityCaptureRateThrottle):
    """Limite separado para o polling; não consome tentativas de captura."""

    scope = "identity_status"


class IdentityPreviewRateThrottle(IdentityCaptureRateThrottle):
    """Frames leves e não guardadas usadas na captura automática."""

    scope = "identity_preview"


class TokenFlowRateThrottle(_IdentityThrottle):
    scope = "token_flow"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        token = view.kwargs.get("token") or view.kwargs.get("uidb64") or ""
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{_digest(token)}",
        }
