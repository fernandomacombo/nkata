from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .password_reset_api import GENERIC_RESET_MESSAGE, _send_reset_email


class FakeUser(SimpleNamespace):
    def get_email_field_name(self):
        return "email"


@override_settings(
    NKATA_FRONTEND_URL="https://nkata.example",
    DEFAULT_FROM_EMAIL="NKATA <no-reply@nkata.example>",
)
class PasswordResetSecurityTests(SimpleTestCase):
    def fake_user(self):
        return FakeUser(
            pk=7,
            password="pbkdf2_sha256$fakehash",
            last_login=None,
            email="membro@example.com",
            first_name="Marta",
            username="marta",
        )

    @patch("entradas.password_reset_api.send_mail")
    def test_email_aponta_para_frontend_e_nao_contem_senha(self, mocked_send):
        _send_reset_email(self.fake_user())

        self.assertEqual(mocked_send.call_count, 1)
        kwargs = mocked_send.call_args.kwargs
        self.assertIn("https://nkata.example/nova-senha/", kwargs["message"])
        self.assertNotIn("pbkdf2_sha256", kwargs["message"])
        self.assertEqual(kwargs["recipient_list"], ["membro@example.com"])

    def test_mensagem_publica_nao_confirma_existencia_da_conta(self):
        texto = GENERIC_RESET_MESSAGE.lower()
        self.assertIn("se existir uma conta", texto)
        self.assertNotIn("conta encontrada", texto)
        self.assertNotIn("email não existe", texto)
