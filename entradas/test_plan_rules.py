from django.test import SimpleTestCase

from .plan_service import PLAN_DEFINITIONS, RECHARGE_PACKS, build_quota_snapshot


class PlanRulesTests(SimpleTestCase):
    def test_os_tres_planos_estao_definidos(self):
        self.assertEqual(set(PLAN_DEFINITIONS), {"LIVRE", "ESSENCIAL", "PREMIUM"})
        self.assertEqual(PLAN_DEFINITIONS["LIVRE"]["daily_signal_limit"], 3)
        self.assertEqual(PLAN_DEFINITIONS["ESSENCIAL"]["daily_signal_limit"], 15)
        self.assertEqual(PLAN_DEFINITIONS["PREMIUM"]["daily_signal_limit"], 40)

    def test_media_do_chat_exige_plano_pago(self):
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["chat_audio"])
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["chat_video"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["chat_audio"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["chat_video"])

    def test_recargas_previstas_sao_10_30_e_80(self):
        self.assertEqual(set(RECHARGE_PACKS), {10, 30, 80})

    def test_recarga_so_e_usada_depois_da_franquia_do_plano(self):
        quota = build_quota_snapshot("LIVRE", sent_today=2, recharge_balance=10)
        self.assertEqual(quota["next_source"], "PLAN")
        self.assertEqual(quota["remaining_today"], 1)
        self.assertEqual(quota["recharge_balance"], 10)

        quota = build_quota_snapshot("LIVRE", sent_today=3, recharge_balance=10)
        self.assertEqual(quota["next_source"], "RECHARGE")
        self.assertFalse(quota["limit_reached"])

    def test_sem_plano_disponivel_nem_recarga_o_limite_e_bloqueado(self):
        quota = build_quota_snapshot("ESSENCIAL", sent_today=15, recharge_balance=0)
        self.assertIsNone(quota["next_source"])
        self.assertTrue(quota["limit_reached"])


class CommercialCatalogTests(SimpleTestCase):
    def test_public_offer_has_at_most_four_options_and_requested_price_bounds(self):
        from .plan_service import public_plan_catalog, public_recharge_catalog
        offers = public_plan_catalog() + public_recharge_catalog()
        self.assertLessEqual(len(offers), 4)
        paid_prices = [offer["price_mzn"] for offer in offers if offer["price_mzn"]]
        self.assertEqual(min(paid_prices), 50)
        self.assertEqual(max(paid_prices), 500)
        self.assertTrue(all(50 <= price <= 500 for price in paid_prices))
        self.assertTrue(all(not offer["purchase_enabled"] for offer in offers))

    def test_retired_recharges_remain_readable_but_are_not_advertised(self):
        from .plan_service import public_recharge_catalog, RECHARGE_TYPE_CREDITS
        self.assertEqual([pack["credits"] for pack in public_recharge_catalog()], [10])
        self.assertEqual(RECHARGE_TYPE_CREDITS["RECARGA_SINAIS_30"], 30)
        self.assertEqual(RECHARGE_TYPE_CREDITS["RECARGA_SINAIS_80"], 80)
