from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .test_admin_panel_api import create_request


class OnboardingReminderTests(TestCase):
    @patch("entradas.management.commands.send_nkata_onboarding_reminders.send_branded_email", return_value=1)
    def test_approved_request_gets_current_step_and_one_email_per_day(self, send):
        pedido = create_request("lembrete@nkata.test", status="PENDENTE")
        pedido.status = "APROVADO"
        pedido.save(update_fields=["status"])
        pedido.refresh_from_db()
        self.assertIsNotNone(pedido.onboarding_aprovado_em)
        type(pedido).objects.filter(pk=pedido.pk).update(
            onboarding_aprovado_em=timezone.now() - timedelta(days=1, minutes=1),
        )

        call_command("send_nkata_onboarding_reminders", dry_run=True)
        send.assert_not_called()
        call_command("send_nkata_onboarding_reminders")
        call_command("send_nkata_onboarding_reminders")
        send.assert_called_once()
        self.assertIn("questionário", send.call_args.kwargs["body"])
        self.assertTrue(send.call_args.kwargs["action_url"].endswith(f"/questionario/{pedido.token}/"))
