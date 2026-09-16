from django.core.management.base import BaseCommand
from django.db import connection

from entradas.chat_media_models import MensagemAudioMatchNKATA


class Command(BaseCommand):
    help = (
        "Prepara a tabela isolada de notas de voz do chat NKATA. "
        "Pode ser executado novamente com segurança."
    )

    def handle(self, *args, **options):
        table_name = MensagemAudioMatchNKATA._meta.db_table
        tables = set(connection.introspection.table_names())

        if table_name in tables:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de notas de voz NKATA já estava pronta."
            ))
            return

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(MensagemAudioMatchNKATA)

        self.stdout.write(self.style.SUCCESS(
            "A tabela de notas de voz NKATA foi criada com sucesso."
        ))
