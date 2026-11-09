import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import AcessoPlanoNKATA, AcaoPerfil, PedidoEntrada, PerfilNKATA, PedidoPagamentoNKATA
from .payment_service import PaymentError, start_checkout, reconcile, valid_checkout_url
from .plan_service import assign_plan, plan_code_for_user, recharge_balance_for_user


@override_settings(NKATA_PAYMENTS_ENABLED=True, NKATA_PAYSUITE_TOKEN="test-token",
    NKATA_PAYSUITE_WEBHOOK_SECRET="test-secret", NKATA_PAYMENT_ORIGIN="https://nkata.example",
    NKATA_CHECKOUT_HOSTS=["paysuite.tech"])
class PaymentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="payer", email="payer@example.test")
        pedido = PedidoEntrada.objects.create(nome_completo="Payer", idade=28, email=self.user.email)
        self.profile = PerfilNKATA.objects.create(usuario=self.user, pedido=pedido, nome_publico="Payer", idade=28)
        # Billing tests start from an already-approved active profile.
        PerfilNKATA.objects.filter(pk=self.profile.pk).update(status="ATIVO")
        self.profile.refresh_from_db()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_response(self, method, payment_id=None, payload=None):
        return {"id": "TESTPAYMENT01", "amount": payload["amount"], "reference": payload["reference"],
                "status": "pending", "checkout_url": "https://paysuite.tech/checkout/TESTPAYMENT01"}

    def order(self, product="ESSENCIAL"):
        with patch("entradas.payment_service.provider_request", side_effect=self.create_response):
            return start_checkout(self.user, product, uuid.uuid4())

    def paid_data(self, order, **overrides):
        return {"id": order.provedor_id, "amount": str(order.valor), "reference": order.referencia,
            "status": "completed", "transaction": {"status": "completed", "transaction_id": "TX1"}, **overrides}

    def settle(self, order, data=None):
        with patch("entradas.payment_service.provider_request", return_value=data or self.paid_data(order)):
            return reconcile(order)

    def test_checkout_sets_server_amount_nkata_brand_and_does_not_grant_plan(self):
        with patch("entradas.payment_service.provider_request", side_effect=self.create_response) as provider:
            order = start_checkout(self.user, "ESSENCIAL", uuid.uuid4())
        self.assertEqual(order.valor, Decimal("250"))
        payload = provider.call_args.kwargs["payload"]
        self.assertTrue(payload["reference"].startswith("NKATA"))
        self.assertTrue(payload["reference"].isalnum())
        self.assertIn("NKATA", payload["description"])
        self.assertTrue(payload["webhook_url"].endswith("/api/pagamentos/paysuite/webhook/"))
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")

    def test_client_cannot_set_amount_or_status(self):
        with patch("entradas.payment_service.provider_request") as provider:
            response = self.client.post("/api/minha-conta/pagamentos/", {"product": "PREMIUM", "key": str(uuid.uuid4()), "amount": 1, "status": "paid"}, format="json")
        self.assertEqual(response.status_code, 400)
        provider.assert_not_called()

    def test_same_key_does_not_create_second_provider_request(self):
        key = uuid.uuid4()
        with patch("entradas.payment_service.provider_request", side_effect=self.create_response) as provider:
            first = start_checkout(self.user, "ESSENCIAL", key)
            second = start_checkout(self.user, "ESSENCIAL", key)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(provider.call_count, 1)

    def test_key_cannot_be_reused_for_different_product(self):
        key = uuid.uuid4()
        with patch("entradas.payment_service.provider_request", side_effect=self.create_response):
            start_checkout(self.user, "ESSENCIAL", key)
        with self.assertRaises(PaymentError):
            start_checkout(self.user, "PREMIUM", key)

    def test_timeout_leaves_uncertain_order_without_retrying_charge(self):
        key = uuid.uuid4()
        with patch("entradas.payment_service.provider_request", side_effect=PaymentError("timeout", 503)) as provider:
            with self.assertRaises(PaymentError):
                start_checkout(self.user, "ESSENCIAL", key)
            order = start_checkout(self.user, "ESSENCIAL", key)
            self.assertEqual(provider.call_count, 1)
        self.assertEqual(order.estado, "INCERTO")
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")
        with self.assertRaises(PaymentError):
            start_checkout(self.user, "ESSENCIAL", uuid.uuid4())

    def test_checkout_url_must_belong_to_approved_https_host(self):
        for url in ("javascript:alert(1)", "https://paysuite.tech.evil.test/x", "http://paysuite.tech/x", "https://user@paysuite.tech/x", "https://paysuite.tech:444/x"):
            self.assertFalse(valid_checkout_url(url))
        self.assertTrue(valid_checkout_url("https://paysuite.tech/checkout/id"))

    def test_confirmed_payment_activates_thirty_days_once(self):
        order = self.order()
        now = timezone.now()
        with patch("entradas.payment_service.timezone.now", return_value=now):
            result = self.settle(order)
            again = self.settle(order)
        self.assertEqual(result.estado, "PAGO")
        self.assertEqual(again.aplicado_em, result.aplicado_em)
        access = AcessoPlanoNKATA.objects.get(usuario=self.user)
        self.assertEqual(access.fim, now + timedelta(days=30))
        self.assertEqual(access.origem, "PAYSUITE")

    def test_wrong_reference_amount_currency_or_id_never_unlocks(self):
        order = self.order()
        for changes in ({"amount": "1"}, {"amount": "NaN"}, {"reference": "OTHER"}, {"currency": "USD"}, {"id": "OTHER"}):
            with self.subTest(changes=changes), self.assertRaises(PaymentError):
                self.settle(order, self.paid_data(order, **changes))
        self.assertFalse(AcessoPlanoNKATA.objects.filter(usuario=self.user).exists())

    def test_success_without_completed_transaction_is_not_enough(self):
        order = self.order()
        with self.assertRaises(PaymentError):
            self.settle(order, self.paid_data(order, transaction={"status": "pending"}))
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")

    def test_pending_and_failed_do_not_grant_access(self):
        order = self.order()
        for state in ("pending", "failed"):
            self.settle(order, self.paid_data(order, status=state))
            self.assertEqual(plan_code_for_user(self.user), "LIVRE")
        self.assertEqual(PedidoPagamentoNKATA.objects.get(pk=order.pk).estado, "FALHOU")

    def test_delayed_failed_event_does_not_undo_paid_order(self):
        order = self.order()
        self.settle(order)
        result = self.settle(order, self.paid_data(order, status="failed"))
        self.assertEqual(result.estado, "PAGO")
        self.assertEqual(plan_code_for_user(self.user), "ESSENCIAL")

    def test_recharge_only_adds_credits_once_and_does_not_grant_paid_plan(self):
        order = self.order("RECARGA10")
        self.settle(order)
        self.settle(order)
        self.assertEqual(recharge_balance_for_user(self.user), 10)
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")
        self.assertEqual(AcaoPerfil.objects.filter(tipo="RECARGA_SINAIS_10", usuario=self.user).count(), 1)

    def test_renewal_preserves_unused_days(self):
        assign_plan(self.user, "ESSENCIAL")
        previous_end = AcessoPlanoNKATA.objects.get(usuario=self.user).fim
        order = self.order()
        self.settle(order)
        self.assertEqual(AcessoPlanoNKATA.objects.get(usuario=self.user).fim, previous_end + timedelta(days=30))

    def test_different_active_plan_cannot_be_purchased(self):
        assign_plan(self.user, "PREMIUM")
        with self.assertRaises(PaymentError):
            self.order("ESSENCIAL")

    def test_account_blocked_after_checkout_puts_money_in_review(self):
        order = self.order()
        PerfilNKATA.objects.filter(pk=self.profile.pk).update(status="BLOQUEADO")
        result = self.settle(order)
        self.assertEqual(result.estado, "REVISAO")
        self.assertIsNotNone(result.confirmado_em)
        self.assertIsNone(result.aplicado_em)
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")

    def test_other_user_cannot_view_or_verify_order(self):
        order = self.order()
        other = get_user_model().objects.create_user(username="other")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get("/api/minha-conta/pagamentos/").json()["results"], [])
        self.assertEqual(self.client.post(f"/api/minha-conta/pagamentos/{order.pk}/verificar/").status_code, 404)

    def test_browser_return_is_not_a_payment_confirmation(self):
        order = self.order()
        response = self.client.get(f"/api/minha-conta/pagamentos/?status=completed&nkata_payment={order.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")

    def webhook(self, order, signature=True):
        raw = json.dumps({"event": "payment.success", "data": {"id": order.provedor_id, "reference": order.referencia}}).encode()
        digest = hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest() if signature else "forged"
        return self.client.post("/api/pagamentos/paysuite/webhook/", raw, content_type="application/json", HTTP_X_SIGNATURE=digest)

    def test_webhook_requires_signature_before_contacting_provider(self):
        order = self.order()
        with patch("entradas.payment_service.provider_request") as provider:
            self.assertEqual(self.webhook(order, signature=False).status_code, 403)
            provider.assert_not_called()

    def test_signed_webhook_verifies_provider_and_is_idempotent(self):
        order = self.order()
        with patch("entradas.payment_service.provider_request", return_value=self.paid_data(order)):
            self.assertEqual(self.webhook(order).status_code, 200)
            before = AcessoPlanoNKATA.objects.get(usuario=self.user).fim
            self.assertEqual(self.webhook(order).status_code, 200)
            self.assertEqual(AcessoPlanoNKATA.objects.get(usuario=self.user).fim, before)

    @override_settings(NKATA_PAYMENTS_ENABLED=False)
    def test_disabled_checkout_never_contacts_provider(self):
        with patch("entradas.payment_service.provider_request") as provider, self.assertRaises(PaymentError):
            start_checkout(self.user, "ESSENCIAL", uuid.uuid4())
        provider.assert_not_called()

    def test_csrf_is_required_for_checkout_session(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post("/api/minha-conta/pagamentos/", {"product": "ESSENCIAL", "key": str(uuid.uuid4())}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_provider_request_uses_authentication_and_no_redirects(self):
        from .payment_service import provider_request
        with patch("entradas.payment_service.requests.request") as http:
            http.return_value.json.return_value = {"status": "success", "data": {"id": "PAY1"}}
            self.assertEqual(provider_request("GET", payment_id="PAY1"), {"id": "PAY1"})
        self.assertFalse(http.call_args.kwargs["allow_redirects"])
        self.assertEqual(http.call_args.kwargs["headers"]["Authorization"], "Bearer test-token")
        self.assertEqual(http.call_args.args[1], "https://paysuite.tech/api/v1/payments/PAY1")

    def test_provider_outage_does_not_leak_secret_or_response(self):
        import requests
        from .payment_service import provider_request
        with patch("entradas.payment_service.requests.request", side_effect=requests.Timeout("test-token sensitive-body")):
            with self.assertRaises(PaymentError) as error:
                provider_request("GET", payment_id="PAY1")
        self.assertNotIn("test-token", str(error.exception))
        self.assertNotIn("sensitive-body", str(error.exception))

    def test_signed_but_wrong_provider_state_does_not_grant(self):
        order = self.order()
        with patch("entradas.payment_service.provider_request", return_value=self.paid_data(order, status="pending")):
            self.assertEqual(self.webhook(order).status_code, 200)
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")

    def test_malformed_signed_json_is_rejected(self):
        raw = b"[]"
        digest = hmac.new(b"test-secret", raw, hashlib.sha256).hexdigest()
        response = self.client.post("/api/pagamentos/paysuite/webhook/", raw, content_type="application/json", HTTP_X_SIGNATURE=digest)
        self.assertEqual(response.status_code, 400)

    def test_untrusted_checkout_address_does_not_reach_client(self):
        def malicious(method, payment_id=None, payload=None):
            return {**self.create_response(method, payment_id, payload), "checkout_url": "https://evil.test/pay"}
        with patch("entradas.payment_service.provider_request", side_effect=malicious), self.assertRaises(PaymentError):
            start_checkout(self.user, "ESSENCIAL", uuid.uuid4())
        order = PedidoPagamentoNKATA.objects.get(usuario=self.user)
        self.assertEqual(order.estado, "INCERTO")
        self.assertFalse(order.checkout_url)
        self.assertEqual(order.provedor_id, "TESTPAYMENT01")

    def test_provider_returning_wrong_reference_does_not_unlock(self):
        def wrong(method, payment_id=None, payload=None):
            return {**self.create_response(method, payment_id, payload), "reference": "OTHER"}
        with patch("entradas.payment_service.provider_request", side_effect=wrong), self.assertRaises(PaymentError):
            start_checkout(self.user, "ESSENCIAL", uuid.uuid4())
        self.assertEqual(plan_code_for_user(self.user), "LIVRE")

    def test_signed_callback_during_creation_requests_retry(self):
        order = self.order()
        provider_id = order.provedor_id
        PedidoPagamentoNKATA.objects.filter(pk=order.pk).update(provedor_id=None)
        self.assertEqual(order.provedor_id, provider_id)
        self.assertEqual(self.webhook(order).status_code, 503)

    def test_fulfillment_rolls_back_if_recharge_write_fails(self):
        order = self.order("RECARGA10")
        with patch("entradas.payment_service.grant_recharge", side_effect=RuntimeError("database failed")):
            with self.assertRaises(RuntimeError):
                self.settle(order)
        order.refresh_from_db()
        self.assertIsNone(order.aplicado_em)
        self.assertEqual(recharge_balance_for_user(self.user), 0)
        self.settle(order)
        self.assertEqual(recharge_balance_for_user(self.user), 10)
