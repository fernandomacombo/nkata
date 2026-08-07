from django.test import SimpleTestCase

from .signal_views import FREE_DAILY_SIGNAL_LIMIT, SIGNAL_DEFINITIONS, build_signal_quota


class SignalRulesTests(SimpleTestCase):
    def test_plano_livre_tem_tres_sinais_por_dia(self):
        self.assertEqual(FREE_DAILY_SIGNAL_LIMIT, 3)
        self.assertEqual(set(SIGNAL_DEFINITIONS), {"FLOR", "BEIJINHO", "OLA"})

    def test_quota_inicial_tem_tres_disponiveis(self):
        quota = build_signal_quota(0)
        self.assertEqual(quota["used_today"], 0)
        self.assertEqual(quota["remaining_today"], 3)
        self.assertFalse(quota["limit_reached"])

    def test_terceiro_sinal_atinge_limite(self):
        quota = build_signal_quota(3)
        self.assertEqual(quota["used_today"], 3)
        self.assertEqual(quota["remaining_today"], 0)
        self.assertTrue(quota["limit_reached"])

    def test_quota_nunca_fica_negativa(self):
        quota = build_signal_quota(20)
        self.assertEqual(quota["used_today"], 3)
        self.assertEqual(quota["remaining_today"], 0)
        self.assertTrue(quota["limit_reached"])
