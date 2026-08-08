from django.apps import AppConfig


class EntradasConfig(AppConfig):
    name = "entradas"

    def ready(self):
        from . import access_email_notifications  # noqa: F401
        from . import account_lifecycle  # noqa: F401
        from . import notification_signals  # noqa: F401
        from .admin_workflow import aplicar_fluxo_de_aprovacao_admin

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

        # Momentos, Publicações e denúncias usam tabelas isoladas das migrações
        # antigas, mas precisam de filas próprias no Django Admin.
        from . import moments_admin  # noqa: F401
        from . import posts_admin  # noqa: F401
        from . import post_safety_admin  # noqa: F401

        aplicar_fluxo_de_aprovacao_admin()
