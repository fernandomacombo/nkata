from django.test import TestCase
from django.contrib.auth import get_user_model
from .test_conversations import profile
from .models import CarteiraNKATA, MovimentoCreditoNKATA
from .wallet_service import record_movement, wallet_snapshot, reconcile_balance, grant_welcome_credits, WalletError


class WalletTests(TestCase):
    def setUp(self):
        self.a, self.b = profile(90).usuario, profile(91).usuario

    def move(self, key="pay:1", amount=50, kind="RECARGA"):
        return record_movement(self.a, key=key, amount=amount, kind=kind, reference=key, reason="Teste financeiro")

    def test_idempotent_credit_and_debit(self):
        first = self.move()
        self.assertEqual(self.move().pk, first.pk)
        self.move("signal:1", -2, "CONSUMO")
        self.assertEqual(wallet_snapshot(self.a)["saldo"], 48)
        self.assertEqual(MovimentoCreditoNKATA.objects.count(), 2)
        self.assertTrue(reconcile_balance(CarteiraNKATA.objects.get(usuario=self.a))["consistente"])

    def test_conflicting_retry_and_insufficient_balance(self):
        self.move()
        with self.assertRaises(WalletError):
            self.move(amount=100)
        with self.assertRaises(WalletError):
            self.move("too-much", -51, "CONSUMO")
        self.assertEqual(wallet_snapshot(self.a)["saldo"], 50)
        self.assertEqual(MovimentoCreditoNKATA.objects.count(), 1)

    def test_transaction_immutable_via_instance(self):
        movement = self.move()
        movement.quantidade = 100
        with self.assertRaises(ValueError):
            movement.save()
        with self.assertRaises(ValueError):
            movement.delete()

    def test_own_wallet_read_only(self):
        self.move()
        self.client.force_login(self.b)
        url = "/api/minha-conta/carteira/"
        response = self.client.get(url + f"?usuario={self.a.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saldo"], 0)
        self.assertEqual(self.client.post(url, {"saldo": 10000}).status_code, 405)
        self.assertFalse(CarteiraNKATA.objects.filter(usuario=self.b).exists())

    def test_no_welcome_without_actual_verification(self):
        with self.assertRaises(WalletError):
            grant_welcome_credits(self.a)
        self.assertFalse(CarteiraNKATA.objects.filter(usuario=self.a).exists())

    def test_admin_has_no_member_wallet(self):
        admin = get_user_model().objects.create_user("wallet-admin", is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/api/minha-conta/carteira/").status_code, 403)


    def test_credit_chat_pass_is_idempotent_global_and_expires(self):
        from uuid import uuid4
        from datetime import timedelta
        from django.utils import timezone
        from .models import AcessoChatCreditoNKATA
        from .plan_service import plan_for_user
        from .wallet_service import unlock_chat
        self.move()
        key = uuid4()
        with self.settings(NKATA_CREDIT_SPENDING_ENABLED=True):
            access, charged = unlock_chat(self.a, key=key, expected_cost=10)
            self.assertTrue(charged)
            self.assertEqual(access.fim-access.inicio, timedelta(hours=24))
            self.assertFalse(unlock_chat(self.a, key=key, expected_cost=10)[1])
            self.assertFalse(unlock_chat(self.a, key=uuid4(), expected_cost=10)[1])
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 40)
            self.assertTrue(plan_for_user(self.a)["features"]["chat_text"])
            self.assertFalse(plan_for_user(self.a)["features"]["chat_audio"])
            AcessoChatCreditoNKATA.objects.filter(pk=access.pk).update(inicio=timezone.now()-timedelta(days=2), fim=timezone.now()-timedelta(days=1))
            self.assertFalse(plan_for_user(self.a)["features"]["chat_text"])
            self.assertFalse(unlock_chat(self.a, key=key, expected_cost=10)[1])
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 40)


    def test_signal_cost_requires_confirmation_and_charges_once(self):
        from .models import AcaoPerfil, Conversa
        self.move()
        self.client.force_login(self.a)
        url = f"/api/perfis/{self.b.perfil_nkata.pk}/sinais/"
        with self.settings(NKATA_CREDIT_SPENDING_ENABLED=True):
            self.assertEqual(self.client.post(url, {"tipo": "FLOR", "expected_cost": 1}).status_code, 409)
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 50)
            self.assertEqual(self.client.post(url, {"tipo": "FLOR", "expected_cost": 2}).status_code, 201)
            self.assertEqual(self.client.post(url, {"tipo": "FLOR", "expected_cost": 2}).status_code, 409)
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 48)
            self.assertEqual(AcaoPerfil.objects.filter(usuario=self.a, tipo="SINAL_FLOR").count(), 1)
            self.assertFalse(Conversa.objects.exists())
