from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .models import QuestionarioEntrada
from .test_governance_rules import create_member


class ReactivationTests(TestCase):
    @patch("entradas.management.commands.send_nkata_reactivation.send_branded_email", return_value=1)
    def test_preview_and_single_delivery_to_inactive_complete_account(self, send):
        member, profile = create_member()
        recent, recent_profile = create_member("recent@example.test")
        incomplete, incomplete_profile = create_member("incomplete@example.test")
        QuestionarioEntrada.objects.create(pedido=profile.pedido)
        QuestionarioEntrada.objects.create(pedido=recent_profile.pedido)
        users = get_user_model().objects
        users.filter(pk__in=[member.pk, incomplete.pk]).update(
            last_login=timezone.now() - timedelta(days=8),
        )
        users.filter(pk=recent.pk).update(last_login=timezone.now())

        call_command("send_nkata_reactivation")
        send.assert_not_called()
        call_command("send_nkata_reactivation", send=True)
        call_command("send_nkata_reactivation", send=True)

        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["recipient"], member.email)
        profile.refresh_from_db()
        incomplete_profile.refresh_from_db()
        self.assertIsNotNone(profile.reativacao_enviada_em)
        self.assertIsNone(incomplete_profile.reativacao_enviada_em)
