from django.core.management.base import BaseCommand
from django.db import connection

from entradas.posts_models import PublicacaoNKATA, ReacaoPublicacaoNKATA


class Command(BaseCommand):
    help = (
        "Prepara as tabelas isoladas de Publicações NKATA e respetivas reações. "
        "Pode ser executado novamente com segurança."
    )

    def _table_names(self):
        return set(connection.introspection.table_names())

    def _ensure_model_table(self, model, label):
        table_name = model._meta.db_table
        if table_name in self._table_names():
            self.stdout.write(self.style.SUCCESS(f"{label} já estava pronta."))
            return False

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(model)

        self.stdout.write(self.style.SUCCESS(f"{label} criada com sucesso."))
        return True

    def handle(self, *args, **options):
        self._ensure_model_table(
            PublicacaoNKATA,
            "A tabela de Publicações NKATA",
        )
        self._ensure_model_table(
            ReacaoPublicacaoNKATA,
            "A tabela de reações das Publicações NKATA",
        )
