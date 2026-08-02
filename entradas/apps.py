from django.apps import AppConfig


class EntradasConfig(AppConfig):
    name = "entradas"

    def ready(self):
        # O modelo e os sinais ficam separados para manter models.py organizado.
        from . import notification_models  # noqa: F401
        from . import notification_signals  # noqa: F401
