from io import StringIO
from uuid import uuid4
from django.core.management import call_command, CommandError
from django.test import TestCase
from django.utils import timezone
from .test_conversations import profile
from .wallet_service import record_movement
from .models import CarteiraNKATA, PedidoPagamentoNKATA


class CreditAuditTests(TestCase):
    def test_read_only_audit_detects_missing_payment_credit_and_bad_balance(self):
        user = profile(94).usuario
        order = PedidoPagamentoNKATA.objects.create(usuario=user, chave=uuid4(), referencia="AUDITTEST", produto="CREDITOS_POPULAR",
            valor=250, creditos=275, estado="PAGO", confirmado_em=timezone.now(), aplicado_em=timezone.now())
        # TestCase wraps in a transaction; the command normally gets its own
        # independent read-only snapshot on PostgreSQL.
        from unittest.mock import patch
        with patch("entradas.management.commands.auditar_creditos.connection.vendor", "sqlite"):
            with self.assertRaises(CommandError):
                call_command("auditar_creditos", stdout=StringIO(), stderr=StringIO())
            record_movement(user, key=f"paysuite:{order.pk}", kind="RECARGA", amount=275, reference=order.referencia, reason="Recarga")
            output = StringIO()
            call_command("auditar_creditos", stdout=output, stderr=StringIO())
            self.assertIn("ocorrências: 0", output.getvalue())
            CarteiraNKATA.objects.filter(usuario=user).update(saldo=999)
            with self.assertRaises(CommandError):
                call_command("auditar_creditos", stdout=StringIO(), stderr=StringIO())
            self.assertEqual(CarteiraNKATA.objects.get(usuario=user).saldo, 999)
