from datetime import timedelta

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from .chat_realtime_api import (
    INITIAL_SYNC_SECONDS,
    PRESENCE_TTL_SECONDS,
    TYPING_TTL_SECONDS,
    _parse_since,
)
from .chat_realtime_models import EstadoConversaNKATA


class ChatRealtimeRulesTests(SimpleTestCase):
    def test_estado_realtime_permanece_isolado_de_migrations(self):
        self.assertFalse(EstadoConversaNKATA._meta.managed)
        self.assertEqual(
            EstadoConversaNKATA._meta.db_table,
            "entradas_estadoconversankata",
        )

    def test_estado_realtime_nao_guarda_rascunho_da_mensagem(self):
        field_names = {field.name for field in EstadoConversaNKATA._meta.fields}
        self.assertNotIn("texto", field_names)
        self.assertNotIn("rascunho", field_names)
        self.assertIn("is_typing", field_names)

    def test_typing_expira_antes_da_presenca(self):
        self.assertGreaterEqual(TYPING_TTL_SECONDS, 3)
        self.assertLess(TYPING_TTL_SECONDS, PRESENCE_TTL_SECONDS)

    def test_rota_live_e_especifica_do_match(self):
        self.assertEqual(
            reverse("entradas_api:chat_live", kwargs={"match_id": 14}),
            "/api/minha-conta/matches/14/live/",
        )

    def test_primeira_sincronizacao_tem_janela_curta(self):
        snapshot = timezone.now()
        parsed = _parse_since("", snapshot)
        self.assertEqual(parsed, snapshot - timedelta(seconds=INITIAL_SYNC_SECONDS))
        self.assertLessEqual(INITIAL_SYNC_SECONDS, 60)
