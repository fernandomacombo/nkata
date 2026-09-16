from datetime import timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from .call_history_api import MAX_CALL_HISTORY_ITEMS, _duration_seconds, _status_label
from .call_models import ChamadaMatchNKATA


class CallHistoryRulesTests(SimpleTestCase):
    def test_history_route_is_scoped_to_match(self):
        self.assertEqual(
            reverse("entradas_api:historico_chamadas_match", kwargs={"match_id": 7}),
            "/api/minha-conta/matches/7/calls/history/",
        )

    def test_history_has_bounded_size(self):
        self.assertGreaterEqual(MAX_CALL_HISTORY_ITEMS, 20)
        self.assertLessEqual(MAX_CALL_HISTORY_ITEMS, 100)

    def test_missed_call_wording_depends_on_direction(self):
        call = SimpleNamespace(
            estado=ChamadaMatchNKATA.ESTADO_PERDIDA,
            iniciador_id=10,
        )
        self.assertEqual(_status_label(call, 10), "Chamada não atendida")
        self.assertEqual(_status_label(call, 20), "Chamada perdida")

    def test_duration_uses_answered_to_ended_interval(self):
        answered = timezone.now()
        call = SimpleNamespace(
            estado=ChamadaMatchNKATA.ESTADO_TERMINADA,
            atendida_em=answered,
            terminada_em=answered + timedelta(seconds=137),
        )
        self.assertEqual(_duration_seconds(call), 137)

    def test_unanswered_call_has_zero_duration(self):
        call = SimpleNamespace(
            estado=ChamadaMatchNKATA.ESTADO_PERDIDA,
            atendida_em=None,
            terminada_em=timezone.now(),
        )
        self.assertEqual(_duration_seconds(call), 0)
