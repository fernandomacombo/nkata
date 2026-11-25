import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from .legacy_commercial import legacy_audit
from .models import PedidoPagamentoNKATA


@override_settings(NKATA_LEGACY_TEST_ORDER_REFERENCES=["TESTPENDING", "TESTPAID", "TESTLATE"])
class LegacyTestOrderAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="legacy-audit")

    def order(self, reference, state, **fields):
        return PedidoPagamentoNKATA.objects.create(
            usuario=self.user, chave=uuid.uuid4(), referencia=reference,
            produto="RECARGA10", valor=50, estado=state, **fields
        )

    def test_only_explicitly_reviewed_orders_are_exempt(self):
        now = timezone.now()
        pending = self.order("TESTPENDING", "PENDENTE")
        paid = self.order("TESTPAID", "PAGO", confirmado_em=now, aplicado_em=now)
        self.order("UNKNOWN", "PENDENTE")
        self.order("TESTLATE", "REVISAO", confirmado_em=now)
        audit = legacy_audit()
        self.assertEqual(audit["legacy_orders"], 4)
        self.assertEqual(audit["legacy_payment_blockers"], 2)
        self.assertEqual(audit["legacy_test_orders_acknowledged"], 2)
        pending.refresh_from_db()
        paid.refresh_from_db()
        self.assertEqual(pending.estado, "PENDENTE")
        self.assertEqual(paid.estado, "PAGO")
        self.assertFalse(paid.simulado)
        self.assertEqual(paid.aplicado_em, now)

    def test_new_confirmation_reopens_review(self):
        order = self.order("TESTPENDING", "PENDENTE")
        self.assertEqual(legacy_audit()["legacy_payment_blockers"], 0)
        PedidoPagamentoNKATA.objects.filter(pk=order.pk).update(
            estado="REVISAO", confirmado_em=timezone.now()
        )
        self.assertEqual(legacy_audit()["legacy_payment_blockers"], 1)

    @override_settings(NKATA_LEGACY_TEST_ORDER_REFERENCES=[])
    def test_default_preserves_original_guard(self):
        self.order("TESTPENDING", "PENDENTE")
        self.assertEqual(legacy_audit()["legacy_payment_blockers"], 1)
