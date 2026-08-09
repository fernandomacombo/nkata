from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q

from entradas.models import AcaoPerfil, MatchPerfil
from entradas.notification_models import NotificacaoNKATA


class Command(BaseCommand):
    help = (
        "Cria a tabela de notificações do NKATA quando necessário e "
        "prepara avisos para interesses, matches e mensagens já existentes."
    )

    def _ensure_table(self):
        table_name = NotificacaoNKATA._meta.db_table
        existing_tables = set(connection.introspection.table_names())

        if table_name in existing_tables:
            return False

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(NotificacaoNKATA)

        return True

    def _active_match(self, perfil_a, perfil_b):
        perfil_1, perfil_2 = sorted([perfil_a, perfil_b], key=lambda perfil: perfil.id)
        return MatchPerfil.objects.filter(
            perfil_1=perfil_1,
            perfil_2=perfil_2,
            status="ATIVO",
        ).first()

    def _backfill_interests(self):
        updated = 0
        interesses = (
            AcaoPerfil.objects
            .filter(tipo="INTERESSE", usuario__isnull=False)
            .select_related(
                "usuario",
                "usuario__perfil_nkata",
                "perfil",
                "perfil__usuario",
            )
        )

        for interesse in interesses:
            destinatario = interesse.perfil.usuario
            perfil_ator = getattr(interesse.usuario, "perfil_nkata", None)

            if not destinatario or destinatario.id == interesse.usuario_id or not perfil_ator:
                continue

            if self._active_match(perfil_ator, interesse.perfil):
                continue

            nome = perfil_ator.nome_publico
            NotificacaoNKATA.objects.update_or_create(
                destinatario=destinatario,
                chave=f"interesse:{interesse.pk}",
                defaults={
                    "ator": interesse.usuario,
                    "perfil": perfil_ator,
                    "match": None,
                    "tipo": "INTERESSE",
                    "titulo": "Novo interesse",
                    "texto": f"{nome} demonstrou interesse no seu perfil.",
                    "lida": False,
                },
            )
            updated += 1

        return updated

    def _backfill_matches_and_messages(self):
        matches_updated = 0
        messages_updated = 0
        matches = (
            MatchPerfil.objects
            .filter(status="ATIVO")
            .select_related(
                "perfil_1",
                "perfil_1__usuario",
                "perfil_2",
                "perfil_2__usuario",
            )
            .prefetch_related("mensagens")
        )

        for match in matches:
            pares = [
                (match.perfil_1, match.perfil_2),
                (match.perfil_2, match.perfil_1),
            ]

            for perfil_destino, outro_perfil in pares:
                if not perfil_destino.usuario_id:
                    continue

                NotificacaoNKATA.objects.filter(
                    destinatario_id=perfil_destino.usuario_id,
                    perfil_id=outro_perfil.id,
                    tipo="INTERESSE",
                ).delete()

                NotificacaoNKATA.objects.update_or_create(
                    destinatario_id=perfil_destino.usuario_id,
                    chave=f"match:{match.id}",
                    defaults={
                        "ator_id": outro_perfil.usuario_id,
                        "perfil": outro_perfil,
                        "match": match,
                        "tipo": "MATCH",
                        "titulo": "É um match",
                        "texto": (
                            f"O interesse entre si e {outro_perfil.nome_publico} "
                            "é mútuo."
                        ),
                        "lida": False,
                    },
                )
                matches_updated += 1

            ultima_nao_lida = (
                match.mensagens
                .filter(lida=False, remetente__isnull=False)
                .select_related("remetente", "remetente__perfil_nkata")
                .order_by("-criado_em")
                .first()
            )

            if not ultima_nao_lida:
                continue

            perfil_remetente = getattr(ultima_nao_lida.remetente, "perfil_nkata", None)
            if not perfil_remetente:
                continue

            if match.perfil_1_id == perfil_remetente.id:
                perfil_destino = match.perfil_2
            elif match.perfil_2_id == perfil_remetente.id:
                perfil_destino = match.perfil_1
            else:
                continue

            if not perfil_destino.usuario_id:
                continue

            resumo = " ".join(ultima_nao_lida.texto.split())
            if len(resumo) > 95:
                resumo = f"{resumo[:92].rstrip()}…"

            NotificacaoNKATA.objects.update_or_create(
                destinatario_id=perfil_destino.usuario_id,
                chave=f"mensagem:{match.id}",
                defaults={
                    "ator": ultima_nao_lida.remetente,
                    "perfil": perfil_remetente,
                    "match": match,
                    "tipo": "MENSAGEM",
                    "titulo": f"Mensagem de {perfil_remetente.nome_publico}",
                    "texto": resumo,
                    "lida": False,
                },
            )
            messages_updated += 1

        return matches_updated, messages_updated

    def handle(self, *args, **options):
        created = self._ensure_table()
        interests = self._backfill_interests()
        matches, messages = self._backfill_matches_and_messages()

        if created:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de notificações foi criada com sucesso."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "A tabela de notificações já estava pronta."
            ))

        self.stdout.write(self.style.SUCCESS(
            "Notificações preparadas: "
            f"{interests} interesses, {matches} matches e {messages} mensagens."
        ))
