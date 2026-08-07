from django.core.management.base import BaseCommand
from django.db import connection

from entradas.moments_models import MomentoNKATA


class Command(BaseCommand):
    help = "Cria a tabela dos Momentos NKATA quando ainda não existir."

    def handle(self, *args, **options):
        table_name = MomentoNKATA._meta.db_table
        existing_tables = set(connection.introspection.table_names())

        if table_name in existing_tables:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de Momentos NKATA já estava pronta."
            ))
            return

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(MomentoNKATA)

        self.stdout.write(self.style.SUCCESS(
            "A tabela de Momentos NKATA foi criada com sucesso."
        ))
