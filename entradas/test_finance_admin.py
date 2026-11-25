import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import CarteiraNKATA, PedidoPagamentoNKATA
from .test_conversations import profile
from .user_roles import set_admin_capabilities
from .wallet_service import record_movement


class FinanceAdminTests(TestCase):
    def setUp(self):
        self.member = profile(98).usuario
        self.staff = get_user_model().objects.create_user("finance-staff", is_staff=True)
        self.client = APIClient()
        self.url = "/api/painel/financas/"
        record_movement(self.member, key="test:recarga", kind="RECARGA", amount=275, reference="test", reason="Recarga")
        record_movement(self.member, key="test:flor", kind="CONSUMO", amount=-2, reference="test:flor", reason="Flor")
        record_movement(self.member, key="test:bonus", kind="BONUS", amount=5, reference="test:bonus", reason="Bónus")
        for product, state, value in (("CREDITOS_POPULAR", "PAGO", 250), ("CREDITOS_INICIAL", "PENDENTE", 50), ("ESSENCIAL", "PAGO", 250)):
            paid = timezone.now() if state == "PAGO" else None
            PedidoPagamentoNKATA.objects.create(usuario=self.member, chave=uuid.uuid4(), referencia=uuid.uuid4().hex,
                produto=product, valor=value, creditos=275 if product=="CREDITOS_POPULAR" else 50 if product.startswith("CREDITOS_") else 0,
                estado=state, confirmado_em=paid, aplicado_em=paid)

    def login_finance(self):
        set_admin_capabilities(self.staff, ["finance"])
        self.client.force_authenticate(self.staff)

    def test_finance_is_separate_read_only_permission(self):
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(self.staff)
        set_admin_capabilities(self.staff, ["members", "overview"])
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.login_finance()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"saldo":99999}).status_code, 405)

    def test_metrics_exclude_old_plans_and_pending_revenue(self):
        self.login_finance()
        data = self.client.get(self.url).data["metrics"]
        self.assertEqual(data["settled_revenue_mzn"], "250")
        self.assertEqual(data["settled_count"], 1)
        self.assertEqual(data["pending_count"], 1)
        self.assertEqual(data["total_balance"], 278)
        self.assertEqual(data["consumed_credits"], 2)
        self.assertEqual(data["bonus_credits"], 5)

    def test_sections_and_reconciliation(self):
        self.login_finance()
        for section, count in (("wallets",1),("payments",2),("movements",3),("consumption",1),("bonuses",1),("audit",0)):
            self.assertEqual(self.client.get(self.url, {"section":section}).data["total"], count, section)
        self.assertEqual(self.client.get(self.url, {"section":"payments","status":"PENDENTE"}).data["total"],1)
        self.assertEqual(self.client.get(self.url, {"section":"wallets","q":"no-such-user"}).data["total"],0)
        self.assertEqual(self.client.get(self.url, {"section":"wallets","offset":-1}).status_code,400)
        CarteiraNKATA.objects.filter(usuario=self.member).update(saldo=100)
        result = self.client.get(self.url, {"section":"audit"}).data
        self.assertEqual(result["total"],1)
        self.assertFalse(result["results"][0]["consistent"])
        self.assertEqual(CarteiraNKATA.objects.get(usuario=self.member).saldo,100)

    def test_catalogue_uses_central_order(self):
        self.login_finance()
        catalog = self.client.get(self.url, {"section":"catalogue"}).data["catalogue"]
        self.assertEqual([(a["code"],a["credits"]) for a in catalog["actions"][:3]], [("OLA",1),("FLOR",2),("BEIJINHO",3)])
        self.assertEqual([p["price_mzn"] for p in catalog["packs"]],[50,100,250,500])
