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


class TokenFlowRateThrottle(_IdentityThrottle):
    scope = "token_flow"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        token = view.kwargs.get("token") or view.kwargs.get("uidb64") or ""
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{_digest(token)}",
        }
