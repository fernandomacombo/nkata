from django.test import SimpleTestCase

from .account_security_api import password_change_errors


class FakeUser:
    def __init__(self, password="AtualSegura123!"):
        self.password = password

    def check_password(self, candidate):
        return candidate == self.password


class AccountPasswordChangeSecurityTests(SimpleTestCase):
    def setUp(self):
        self.user = FakeUser()

    def test_rejeita_palavra_passe_atual_incorreta(self):
        errors = password_change_errors(
            self.user,
            "Errada123!",
            "NovaSegura456!",
            "NovaSegura456!",
        )
        self.assertIn("current_password", errors)

    def test_rejeita_nova_palavra_passe_igual_a_atual(self):
        errors = password_change_errors(
            self.user,
            "AtualSegura123!",
            "AtualSegura123!",
            "AtualSegura123!",
        )
        self.assertIn("new_password", errors)

    def test_rejeita_confirmacao_diferente(self):
        errors = password_change_errors(
            self.user,
            "AtualSegura123!",
            "NovaSegura456!",
            "OutraSegura789!",
        )
        self.assertIn("confirmation", errors)

    def test_fluxo_basico_valido_nao_tem_erros_de_formulario(self):
        errors = password_change_errors(
            self.user,
            "AtualSegura123!",
            "NovaSegura456!",
            "NovaSegura456!",
        )
        self.assertEqual(errors, {})
