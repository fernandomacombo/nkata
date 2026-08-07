from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from entradas.moments_models import MomentoNKATA


class Command(BaseCommand):
    help = (
        "Cria a tabela dos Momentos NKATA quando necessário e acrescenta "
        "campos de moderação em instalações anteriores."
    )

    moderation_fields = (
        "moderacao_status",
        "moderacao_motivo",
        "moderado_em",
    )

    def _column_names(self, table_name):
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
        return {column.name for column in description}

    def handle(self, *args, **options):
        table_name = MomentoNKATA._meta.db_table
        existing_tables = set(connection.introspection.table_names())

        if table_name not in existing_tables:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(MomentoNKATA)

            self.stdout.write(self.style.SUCCESS(
                "A tabela de Momentos NKATA foi criada com moderação ativa."
            ))
            return

        columns = self._column_names(table_name)
        added = []
        with connection.schema_editor() as schema_editor:
            for field_name in self.moderation_fields:
                field = MomentoNKATA._meta.get_field(field_name)
                if field.column in columns:
                    continue
                schema_editor.add_field(MomentoNKATA, field)
                added.append(field_name)

        # Conteúdo anterior à política de moderação não pode permanecer público.
        # Texto livre legado é rejeitado automaticamente; foto/vídeo antigo volta
        # para a fila de revisão manual.
        if "moderacao_status" in added:
            now = timezone.now()
            legacy_text = MomentoNKATA.objects.filter(media="").update(
                moderacao_status="REJEITADO",
                moderacao_motivo=(
                    "Momento antigo removido porque texto livre deixou de ser permitido."
                ),
                moderado_em=now,
            )
            legacy_media = MomentoNKATA.objects.exclude(media="").update(
                moderacao_status="PENDENTE",
                moderacao_motivo="",
                moderado_em=None,
            )
            self.stdout.write(
                f"Conteúdo legado protegido: {legacy_text} texto(s) rejeitado(s), "
                f"{legacy_media} media(s) enviado(s) para revisão."
            )

        if added:
            self.stdout.write(self.style.SUCCESS(
                "Momentos atualizados. Campos adicionados: " + ", ".join(added)
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de Momentos NKATA já estava pronta com moderação."
            ))
