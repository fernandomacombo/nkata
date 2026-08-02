from django.core.management.base import BaseCommand
from django.db import connection

from entradas.notification_models import NotificacaoNKATA


class Command(BaseCommand):
    help = "Cria a tabela de notificações do NKATA quando ela ainda não existe."

    def handle(self, *args, **options):
        table_name = NotificacaoNKATA._meta.db_table
        existing_tables = set(connection.introspection.table_names())

        if table_name in existing_tables:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de notificações já está pronta."
            ))
            return

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(NotificacaoNKATA)

        self.stdout.write(self.style.SUCCESS(
            "A tabela de notificações foi criada com sucesso."
        ))
