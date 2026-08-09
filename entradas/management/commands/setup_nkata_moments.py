from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from entradas.moments_models import MomentoNKATA, ReacaoMomentoNKATA


class Command(BaseCommand):
    help = (
        "Prepara as tabelas dos Momentos NKATA, moderação e reações. Pode ser "
        "executado novamente com segurança após uma atualização parcial."
    )

    moderation_fields = (
        "moderacao_status",
        "moderacao_motivo",
        "moderado_em",
    )

    def _table_names(self):
        return set(connection.introspection.table_names())

    def _column_names(self, table_name):
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        return {column.name for column in description}

    def _ensure_moderation_fields(self, table_name):
        """
        Adiciona apenas campos realmente ausentes.

        No SQLite, schema_editor.add_field() pode reconstruir a tabela. Durante
        essa reconstrução outros campos do modelo podem passar a existir também.
        Por isso a lista de colunas é consultada novamente antes de CADA campo.
        """
        added = []

        for field_name in self.moderation_fields:
            field = MomentoNKATA._meta.get_field(field_name)
            columns = self._column_names(table_name)

            if field.column in columns:
                continue

            with connection.schema_editor() as schema_editor:
                schema_editor.add_field(MomentoNKATA, field)

            added.append(field_name)

        return added

    def _protect_legacy_content(self):
        """Rejeita texto livre legado que ainda esteja pendente."""
        now = timezone.now()
        return MomentoNKATA.objects.filter(
            media="",
            moderacao_status="PENDENTE",
        ).update(
            moderacao_status="REJEITADO",
            moderacao_motivo=(
                "Momento antigo removido porque texto livre deixou de ser permitido."
            ),
            moderado_em=now,
        )

    def _ensure_reaction_table(self):
        table_name = ReacaoMomentoNKATA._meta.db_table
        if table_name in self._table_names():
            self.stdout.write(self.style.SUCCESS(
                "A tabela de reações dos Momentos NKATA já estava pronta."
            ))
            return False

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ReacaoMomentoNKATA)

        self.stdout.write(self.style.SUCCESS(
            "A tabela de reações dos Momentos NKATA foi criada com sucesso."
        ))
        return True

    def handle(self, *args, **options):
        table_name = MomentoNKATA._meta.db_table
        created_moments = False

        if table_name not in self._table_names():
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(MomentoNKATA)
            created_moments = True
            self.stdout.write(self.style.SUCCESS(
                "A tabela de Momentos NKATA foi criada com moderação ativa."
            ))

        added = [] if created_moments else self._ensure_moderation_fields(table_name)

        final_columns = self._column_names(table_name)
        missing = [
            field_name
            for field_name in self.moderation_fields
            if MomentoNKATA._meta.get_field(field_name).column not in final_columns
        ]
        if missing:
            raise RuntimeError(
                "A tabela de Momentos continua incompleta. Campos em falta: "
                + ", ".join(missing)
            )

        legacy_text = self._protect_legacy_content()
        if legacy_text:
            self.stdout.write(
                self.style.WARNING(
                    f"Conteúdo legado protegido: {legacy_text} Momento(s) de "
                    "texto livre rejeitado(s)."
                )
            )

        if added:
            self.stdout.write(self.style.SUCCESS(
                "Momentos atualizados. Campos adicionados: " + ", ".join(added)
            ))
        elif not created_moments:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de Momentos NKATA já estava pronta com moderação."
            ))

        self._ensure_reaction_table()
