from django.core.management.base import BaseCommand
from django.db import connection

from entradas.chat_realtime_models import EstadoConversaNKATA


class Command(BaseCommand):
    help = (
        "Prepara a tabela isolada do estado temporário das conversas NKATA. "
        "Pode ser executado novamente com segurança."
    )

    def handle(self, *args, **options):
        table_name = EstadoConversaNKATA._meta.db_table
        tables = set(connection.introspection.table_names())

        if table_name in tables:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de estado realtime do chat NKATA já estava pronta."
            ))
            return

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(EstadoConversaNKATA)

        self.stdout.write(self.style.SUCCESS(
            "A tabela de estado realtime do chat NKATA foi criada com sucesso."
        ))
