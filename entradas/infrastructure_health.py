"""Configuration diagnostics for the superuser dashboard.

No network calls, secret values or external actions are performed here.
Configuration alone cannot prove that a third-party service is healthy.
"""
from django.conf import settings

from .webrtc_credentials import turn_is_configured


def infrastructure_configuration():
    moderation_provider = str(getattr(settings, "NKATA_MEDIA_MODERATION_PROVIDER", "manual") or "manual").strip().lower()
    automated_moderation = moderation_provider != "manual"
    email_backend = str(getattr(settings, "EMAIL_BACKEND", "") or "")
    email_configured = (
        (email_backend == "entradas.email_backend.ZohoAPIEmailBackend" and bool(getattr(settings, "NKATA_ZOHO_API_KEY", "")))
        or (email_backend == "django.core.mail.backends.smtp.EmailBackend" and all([
            getattr(settings, "EMAIL_HOST", ""),
            getattr(settings, "EMAIL_HOST_USER", ""),
            getattr(settings, "EMAIL_HOST_PASSWORD", ""),
        ]))
    )
    payments_enabled = bool(getattr(settings, "NKATA_PAYMENTS_ENABLED", False))
    payments_configured = payments_enabled and all([
        getattr(settings, "NKATA_PAYSUITE_TOKEN", ""),
        getattr(settings, "NKATA_PAYSUITE_WEBHOOK_SECRET", ""),
    ])
    return {
        "turn_configured": turn_is_configured(),
        "turn_label": "Configurado (sem teste de ligação)" if turn_is_configured() else "Por configurar",
        "moderation_automatic": automated_moderation,
        "moderation_mode": "Automática configurada" if automated_moderation else "Revisão humana",
        "email_configured": bool(email_configured),
        "email_label": "Configurado (envio não testado)" if email_configured else "Não verificado",
        "payments_enabled": payments_enabled,
        "payments_configured": bool(payments_configured),
        "payments_label": (
            "Configurado (transações não testadas)" if payments_configured
            else "Por configurar" if payments_enabled else "Desativado"
        ),
    }
