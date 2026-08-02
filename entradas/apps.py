from django.apps import AppConfig


class EntradasConfig(AppConfig):
    name = "entradas"

    def ready(self):
        from . import notification_signals  # noqa: F401
