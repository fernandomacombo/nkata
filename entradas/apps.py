from django.apps import AppConfig


class EntradasConfig(AppConfig):
    name = "entradas"

    def ready(self):
        from . import notification_signals  # noqa: F401

        # Compatibilidade do Django Admin:
        # MensagemPerfil usa o campo `texto`, não `tipo`.
        # O ajuste é aplicado depois do autodiscover do Admin e antes dos
        # system checks, evitando que uma configuração antiga impeça o servidor
        # e os comandos de gestão de iniciarem.
        try:
            from .admin import MensagemPerfilAdmin
        except ImportError:
            return

        MensagemPerfilAdmin.list_display = (
            "perfil",
            "texto",
            "usuario",
            "session_key",
            "criado_em",
        )
        MensagemPerfilAdmin.list_filter = (
            "texto",
            "criado_em",
        )
        MensagemPerfilAdmin.search_fields = (
            "perfil__nome_publico",
            "usuario__username",
            "usuario__email",
            "session_key",
        )
