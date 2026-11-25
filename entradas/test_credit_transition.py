from django.test import TestCase, override_settings
from django.core.management import call_command
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from .test_conversations import profile
from .models import AcessoPlanoNKATA, MovimentoCreditoNKATA
from .plan_service import assign_plan, active_plan_access, grant_recharge, recharge_balance_for_user
from .payment_service import start_checkout, PaymentError
from .wallet_service import grant_welcome_credits, WalletError, credit_balance
from .launch_promotion import complete_registration_password


class CreditTransitionTests(TestCase):
    def setUp(self):
        self.member = profile(97).usuario

    @override_settings(NKATA_CREDIT_TRANSITION_ENABLED=True, NKATA_PAYMENTS_ENABLED=True,
        NKATA_PAYSUITE_TOKEN="test", NKATA_PAYSUITE_WEBHOOK_SECRET="test", NKATA_PAYMENT_ORIGIN="https://nkata.example")
    def test_new_legacy_sales_disabled_existing_benefits_retained(self):
        assign_plan(self.member, "ESSENCIAL")
        original = active_plan_access(self.member).fim
        grant_recharge(self.member, 10)
        with patch("entradas.payment_service.provider_request") as provider:
            for product in ("ESSENCIAL", "RECARGA10"):
                with self.assertRaises(PaymentError):
                    start_checkout(self.member, product, uuid4())
            provider.assert_not_called()
        self.assertEqual(active_plan_access(self.member).fim, original)
        self.assertEqual(recharge_balance_for_user(self.member), 10)

    @override_settings(NKATA_CREDIT_TRANSITION_ENABLED=True)
    def test_no_new_launch_subscription(self):
        self.member.set_unusable_password()
        self.member.save(update_fields=["password"])
        created, promo = complete_registration_password(self.member, "Valid-password-123")
        self.assertTrue(created)
        self.assertFalse(promo)
        self.assertFalse(AcessoPlanoNKATA.objects.filter(usuario=self.member).exists())

    def test_backfill_defaults_to_simulation(self):
        output = StringIO()
        call_command("reconciliar_bonus_creditos", stdout=output)
        self.assertIn("simulação", output.getvalue())
        self.assertEqual(MovimentoCreditoNKATA.objects.count(), 0)
        with self.assertRaises(WalletError):
            grant_welcome_credits(self.member)
        self.assertEqual(credit_balance(self.member), 0)
