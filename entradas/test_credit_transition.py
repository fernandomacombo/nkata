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


    @override_settings(NKATA_CREDIT_TRANSITION_ENABLED=True)
    def test_approved_identity_receives_bonus_once(self):
        from entradas.identity_models import VerificacaoIdentidadeNKATA, nkata_id_expires_at
        from entradas.models import BonusIdentidadeCreditoNKATA
        from entradas.account_limits import document_key
        pedido = self.member.perfil_nkata.pedido
        pedido.documento_chave = document_key("123456789012A")
        pedido.documento_confirmado = True
        pedido.verificacao_apos_entrada = True
        with self.captureOnCommitCallbacks(execute=True):
            pedido.save(update_fields=["documento_chave", "documento_confirmado", "verificacao_apos_entrada"])
            verification = VerificacaoIdentidadeNKATA.objects.create(pedido=pedido, email_hash="a"*64,
                idade_declarada=30, desafio_selfie="teste", status="APROVADA", expira_em=nkata_id_expires_at())
        self.assertEqual(credit_balance(self.member), 5)
        with self.captureOnCommitCallbacks(execute=True):
            verification.save(update_fields=["status"])
        grant_welcome_credits(self.member)
        self.assertEqual(credit_balance(self.member), 5)
        self.assertEqual(BonusIdentidadeCreditoNKATA.objects.count(), 1)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(tipo="BONUS").count(), 1)
        with self.captureOnCommitCallbacks(execute=True):
            verification.status = "REJEITADA"
            verification.save(update_fields=["status"])
        with self.assertRaises(WalletError):
            grant_welcome_credits(self.member)
        self.assertEqual(credit_balance(self.member), 5)
        output = StringIO()
        call_command("reconciliar_bonus_creditos", "--apply", stdout=output)
        self.assertEqual(credit_balance(self.member), 5)


    @override_settings(NKATA_CREDIT_TRANSITION_ENABLED=True)
    def test_launch_promotion_only_receives_five_and_admin_plan_is_preserved(self):
        from datetime import timedelta
        from django.utils import timezone
        from .identity_models import VerificacaoIdentidadeNKATA, nkata_id_expires_at
        from .account_limits import document_key
        from .plan_service import plan_for_user
        pedido = self.member.perfil_nkata.pedido
        pedido.documento_chave = document_key("123456789013A")
        pedido.documento_confirmado = True
        pedido.verificacao_apos_entrada = True
        pedido.save(update_fields=["documento_chave", "documento_confirmado", "verificacao_apos_entrada"])
        VerificacaoIdentidadeNKATA.objects.create(pedido=pedido, email_hash="b"*64,
            idade_declarada=30, desafio_selfie="teste", status="APROVADA", expira_em=nkata_id_expires_at())
        grant_welcome_credits(self.member)
        self.assertEqual(credit_balance(self.member), 5)
        assign_plan(self.member, "QUINZENAL")
        grant_welcome_credits(self.member)
        self.assertEqual(credit_balance(self.member), 5)
        self.assertIsNotNone(active_plan_access(self.member))
        AcessoPlanoNKATA.objects.filter(usuario=self.member).update(origem="PROMO_LANCAMENTO",
            inicio=timezone.now()-timedelta(days=16), fim=timezone.now()-timedelta(days=1))
        self.client.force_login(self.member)
        for _ in range(2):
            response = self.client.post("/api/minha-conta/carteira/boas-vindas/")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["saldo"], 5)
        self.assertEqual(AcessoPlanoNKATA.objects.get(usuario=self.member).origem, "PROMO_LANCAMENTO")
        self.assertIsNone(active_plan_access(self.member))
        self.assertFalse(plan_for_user(self.member)["features"]["chat_text"])
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(carteira__usuario=self.member, tipo="BONUS").count(), 1)


    @override_settings(NKATA_CREDIT_ONLY_ENABLED=True, NKATA_CREDIT_TRANSITION_ENABLED=True, NKATA_CREDIT_SPENDING_ENABLED=True)
    def test_credit_only_ignores_old_entitlements_and_no_free_signal_fallback(self):
        from datetime import timedelta
        from django.utils import timezone
        from .plan_service import plan_for_user, signal_quota_for_user
        now=timezone.now()
        AcessoPlanoNKATA.objects.create(usuario=self.member,plano="QUINZENAL",inicio=now,fim=now+timedelta(days=14),origem="ADMINISTRATIVA")
        self.assertIsNone(active_plan_access(self.member))
        self.assertFalse(plan_for_user(self.member)["features"]["chat_text"])
        quota=signal_quota_for_user(self.member)
        self.assertEqual(quota["remaining_today"],0)
        self.assertTrue(quota["limit_reached"])
        self.assertEqual(quota["next_source"],"WALLET")
        with self.settings(NKATA_CREDIT_SPENDING_ENABLED=False):
            quota=signal_quota_for_user(self.member)
            self.assertIsNone(quota["next_source"])
            self.assertTrue(quota["limit_reached"])
        with self.assertRaises(ValueError):
            assign_plan(self.member,"PREMIUM")
        with self.assertRaises(ValueError):
            grant_recharge(self.member,10)

    @override_settings(NKATA_CREDIT_ONLY_ENABLED=True, NKATA_CREDIT_TRANSITION_ENABLED=True)
    def test_credit_only_grants_admin_quinzenal_five_only(self):
        from datetime import timedelta
        from django.utils import timezone
        from .identity_models import VerificacaoIdentidadeNKATA, nkata_id_expires_at
        from .account_limits import document_key
        pedido=self.member.perfil_nkata.pedido
        pedido.documento_chave=document_key("123456789014A")
        pedido.documento_confirmado=True
        pedido.verificacao_apos_entrada=True
        pedido.save(update_fields=["documento_chave","documento_confirmado","verificacao_apos_entrada"])
        VerificacaoIdentidadeNKATA.objects.create(pedido=pedido,email_hash="c"*64,
            idade_declarada=30,desafio_selfie="teste",status="APROVADA",expira_em=nkata_id_expires_at())
        now=timezone.now()
        AcessoPlanoNKATA.objects.create(usuario=self.member,plano="QUINZENAL",inicio=now,fim=now+timedelta(days=14),origem="ADMINISTRATIVA")
        for _ in range(2):
            grant_welcome_credits(self.member)
            self.assertEqual(credit_balance(self.member),5)
        self.assertEqual(AcessoPlanoNKATA.objects.get(usuario=self.member).origem,"ADMINISTRATIVA")

    def test_legacy_audit_never_assumes_no_real_payment(self):
        from .legacy_commercial import legacy_audit
        from .models import PedidoPagamentoNKATA
        self.assertEqual(legacy_audit()["legacy_payment_blockers"],0)
        PedidoPagamentoNKATA.objects.create(usuario=self.member,chave=uuid4(),referencia="OLDPENDING",produto="QUINZENAL",valor=100,estado="PENDENTE")
        self.assertEqual(legacy_audit()["legacy_payment_blockers"],1)


    @override_settings(NKATA_CREDIT_ONLY_ENABLED=True, NKATA_CREDIT_TRANSITION_ENABLED=True)
    def test_existing_members_backfill_with_clear_pending_identity_status(self):
        from datetime import timedelta
        from django.utils import timezone
        from .identity_models import VerificacaoIdentidadeNKATA, nkata_id_expires_at
        from .account_limits import document_key
        from .wallet_service import welcome_status, record_movement
        now=timezone.now()
        AcessoPlanoNKATA.objects.create(usuario=self.member,plano="QUINZENAL",inicio=now,fim=now+timedelta(days=14),origem="ADMINISTRATIVA")
        record_movement(self.member,key="simulated:example",kind="RECARGA",amount=50,reference="example",reason="Recarga simulada")
        self.assertEqual(welcome_status(self.member)["blocker"],"IDENTITY_REQUIRED")
        call_command("reconciliar_bonus_creditos","--apply",stdout=StringIO())
        self.assertEqual(credit_balance(self.member),50)
        pedido=self.member.perfil_nkata.pedido
        pedido.documento_chave=document_key("123456789015A")
        pedido.documento_confirmado=True
        pedido.verificacao_apos_entrada=True
        pedido.save(update_fields=["documento_chave","documento_confirmado","verificacao_apos_entrada"])
        VerificacaoIdentidadeNKATA.objects.create(pedido=pedido,email_hash="d"*64,
            idade_declarada=30,desafio_selfie="teste",status="APROVADA",expira_em=nkata_id_expires_at())
        for _ in range(2):
            call_command("reconciliar_bonus_creditos","--apply",stdout=StringIO())
            self.assertEqual(credit_balance(self.member),55)
        self.assertEqual(welcome_status(self.member)["credits"],5)
        self.assertFalse(welcome_status(self.member)["claimable"])

    @override_settings(NKATA_RAILWAY_ENVIRONMENT_ID="36306a53-86bc-4a07-9b09-7c42c58f2e43",
        NKATA_CREDIT_ONLY_ENABLED=True, NKATA_PAYMENT_SIMULATION_ENABLED=True,
        NKATA_PAYMENTS_ENABLED=False, EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend")
    def test_regularize_test_conversion_preserves_ledger_and_is_idempotent(self):
        from .wallet_service import record_movement
        from django.core.management.base import CommandError
        record_movement(self.member,key="welcome:v1",kind="BONUS",amount=5,reference="welcome:v1",reason="Boas-vindas")
        record_movement(self.member,key="welcome:launch:v1",kind="BONUS",amount=45,reference="promo:test",reason="Conversão antiga")
        record_movement(self.member,key="simulated:example",kind="RECARGA",amount=50,reference="test",reason="Recarga simulada")
        record_movement(self.member,key="chat:test",kind="CONSUMO",amount=-10,reference="test",reason="Chat")
        call_command("regularizar_bonus_lancamento",stdout=StringIO())
        self.assertEqual(credit_balance(self.member),90)
        for _ in range(2):
            call_command("regularizar_bonus_lancamento","--apply",stdout=StringIO())
            self.assertEqual(credit_balance(self.member),45)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(carteira__usuario=self.member,chave="welcome:launch:v1").count(),1)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(carteira__usuario=self.member,chave="adjust:launch-cancelled:v1").count(),1)
        with self.settings(NKATA_RAILWAY_ENVIRONMENT_ID="production"):
            with self.assertRaises(CommandError):
                call_command("regularizar_bonus_lancamento","--apply",stdout=StringIO())

    @override_settings(NKATA_RAILWAY_ENVIRONMENT_ID="36306a53-86bc-4a07-9b09-7c42c58f2e43",
        NKATA_CREDIT_ONLY_ENABLED=True, NKATA_PAYMENT_SIMULATION_ENABLED=True,
        NKATA_PAYMENTS_ENABLED=False, EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend")
    def test_regularization_does_not_create_debt(self):
        from .wallet_service import record_movement
        record_movement(self.member,key="welcome:launch:v1",kind="BONUS",amount=45,reference="promo:test",reason="Conversão antiga")
        record_movement(self.member,key="chat:test",kind="CONSUMO",amount=-10,reference="test",reason="Chat")
        output=StringIO()
        call_command("regularizar_bonus_lancamento","--apply",stdout=output)
        self.assertIn("review=1",output.getvalue())
        self.assertEqual(credit_balance(self.member),35)
