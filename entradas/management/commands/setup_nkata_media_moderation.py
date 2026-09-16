from django.core.management.base import BaseCommand
from django.db import connection

from entradas.content_moderation_models import AnaliseAutomaticaConteudoNKATA


class Command(BaseCommand):
    help = (
        "Prepara a tabela isolada de pré-moderação automática de media NKATA. "
        "Pode ser executado novamente com segurança."
    )

    def handle(self, *args, **options):
        table_name = AnaliseAutomaticaConteudoNKATA._meta.db_table
        tables = set(connection.introspection.table_names())

        if table_name in tables:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de pré-moderação automática NKATA já estava pronta."
            ))
            return

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(AnaliseAutomaticaConteudoNKATA)

        self.stdout.write(self.style.SUCCESS(
            "A tabela de pré-moderação automática NKATA foi criada com sucesso."
        ))
