from types import SimpleNamespace
from uuid import UUID

from django.test import SimpleTestCase, override_settings

from .access_email_notifications import build_access_status_email


@override_settings(NKATA_FRONTEND_URL="http://localhost:5173")
class AccessEmailNotificationsTests(SimpleTestCase):
    def pedido(self, status, **overrides):
        data = {
            "nome_completo": "Marta Afonso",
            "email": "marta@example.com",
            "status": status,
            "token": UUID("12345678-1234-5678-1234-567812345678"),
            "observacao_admin": "NOTA INTERNA QUE NÃO DEVE SAIR",
        }
        data.update(overrides)
        return SimpleNamespace(**data)

    def test_aprovacao_envia_link_do_questionario_react(self):
        subject, body = build_access_status_email(self.pedido("APROVADO"))

        self.assertIn("aprovado", subject.lower())
        self.assertIn(
            "http://localhost:5173/questionario/12345678-1234-5678-1234-567812345678/",
            body,
        )
        self.assertIn("Não o partilhe", body)

    def test_correcao_nao_expoe_observacao_interna(self):
        subject, body = build_access_status_email(self.pedido("PRECISA_CORRIGIR"))

        self.assertIn("rever", subject.lower())
        self.assertNotIn("NOTA INTERNA", body)
        self.assertIn("acompanhar-pedido", body)

    def test_recusa_nao_inclui_detalhes_internos(self):
        subject, body = build_access_status_email(self.pedido("RECUSADO"))

        self.assertTrue(subject)
        self.assertNotIn("NOTA INTERNA", body)

    def test_estado_nao_notificavel_nao_gera_email(self):
        subject, body = build_access_status_email(self.pedido("EM_ANALISE"))

        self.assertIsNone(subject)
        self.assertIsNone(body)
