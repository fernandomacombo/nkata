from django.core.management.base import BaseCommand
from django.db import connection

from entradas.call_models import ChamadaMatchNKATA, SinalChamadaNKATA


class Command(BaseCommand):
    help = (
        "Prepara as tabelas isoladas de chamadas WebRTC do NKATA. "
        "Pode ser executado novamente com segurança."
    )

    def handle(self, *args, **options):
        tables = set(connection.introspection.table_names())
        created = []

        with connection.schema_editor() as schema_editor:
            if ChamadaMatchNKATA._meta.db_table not in tables:
                schema_editor.create_model(ChamadaMatchNKATA)
                created.append("chamadas")
                tables.add(ChamadaMatchNKATA._meta.db_table)

            if SinalChamadaNKATA._meta.db_table not in tables:
                schema_editor.create_model(SinalChamadaNKATA)
                created.append("sinalização")

        if created:
            self.stdout.write(self.style.SUCCESS(
                "Tabelas NKATA preparadas: " + ", ".join(created) + "."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "As tabelas de chamadas NKATA já estavam prontas."
            ))
