import shutil

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from entradas.payment_service import payments_enabled
from entradas.webrtc_credentials import turn_is_configured


class Command(BaseCommand):
    help = "Verifica tabelas NKATA, áudio e configuração operacional, sem alterar dados."

    def add_arguments(self, parser):
        parser.add_argument("--require-turn", action="store_true")
        parser.add_argument("--require-payments", action="store_true")

    def handle(self, *args, **options):
        from entradas import (call_models, chat_media_models, chat_realtime_models,
            moments_models, posts_models, post_safety_models, notification_models,
            content_moderation_models)  # noqa: F401
        models = [model for model in apps.get_app_config("entradas").get_models()
                  if not model._meta.managed and not model._meta.proxy]
        tables = set(connection.introspection.table_names())
        missing = [model._meta.db_table for model in models if model._meta.db_table not in tables]
        if missing:
            raise CommandError("Aplique as migrações. Tabelas em falta: " + ", ".join(missing))
        with connection.cursor() as cursor:
            for model in models:
                columns = {column.name for column in connection.introspection.get_table_description(cursor, model._meta.db_table)}
                if {field.column for field in model._meta.local_fields} - columns:
                    raise CommandError(f"A tabela {model._meta.db_table} precisa de revisão do esquema.")
        if not shutil.which("ffmpeg"):
            raise CommandError("Instale ffmpeg para validar as notas de voz.")
        if options["require_turn"] and not turn_is_configured():
            raise CommandError("TURN ainda não está configurado para chamadas em redes diferentes.")
        if options["require_payments"] and not payments_enabled():
            raise CommandError("Os pagamentos ainda não estão habilitados e configurados.")
        self.stdout.write(self.style.SUCCESS(f"Runtime NKATA: {len(models)} tabelas e descodificador de áudio verificados."))
        if not turn_is_configured():
            self.stdout.write(self.style.WARNING("TURN: configuração pendente; chamadas em redes diferentes não estão homologadas."))
        if not payments_enabled():
            self.stdout.write("Compras desativadas ou por configurar.")
