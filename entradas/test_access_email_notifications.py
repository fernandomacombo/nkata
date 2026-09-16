from types import SimpleNamespace
from uuid import UUID

from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings

from .access_email_notifications import build_access_receipt_email, build_access_status_email
from .models import PedidoEntrada


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

    def test_correcao_de_identidade_inclui_link_privado_de_nova_captura(self):
        verification = SimpleNamespace(
            status="REPETIR",
            token=UUID("87654321-4321-8765-4321-876543218765"),
        )
        _subject, body = build_access_status_email(self.pedido(
            "PRECISA_CORRIGIR",
            verificacao_identidade=verification,
        ))

        self.assertIn(
            "http://localhost:5173/verificar-identidade/87654321-4321-8765-4321-876543218765/",
            body,
        )
        self.assertNotIn("NOTA INTERNA", body)

    def test_recusa_nao_inclui_detalhes_internos(self):
        subject, body = build_access_status_email(self.pedido("RECUSADO"))

        self.assertTrue(subject)
        self.assertNotIn("NOTA INTERNA", body)

    def test_estado_nao_notificavel_nao_gera_email(self):
        subject, body = build_access_status_email(self.pedido("EM_ANALISE"))

        self.assertIsNone(subject)
        self.assertIsNone(body)

    def test_recibo_inclui_codigo_e_link_de_acompanhamento(self):
        subject, body = build_access_receipt_email(self.pedido("PENDENTE"))

        self.assertIn("código", subject.lower())
        self.assertIn("12345678-1234-5678-1234-567812345678", body)
        self.assertIn("http://localhost:5173/acompanhar-pedido/", body)
        self.assertNotIn("NOTA INTERNA", body)


@override_settings(
    NKATA_FRONTEND_URL="https://www.nkata.co.mz",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccessStatusNotificationSignalTests(TestCase):
    def test_approval_sends_questionnaire_link_automatically(self):
        with self.captureOnCommitCallbacks(execute=True):
            pedido = PedidoEntrada.objects.create(
                nome_completo="Pessoa Aprovada",
                email="aprovada@example.com",
                telefone="840000000",
                idade=31,
                cidade="Maputo",
                genero="FEMININO",
                objetivo="RELACIONAMENTO_SERIO",
                aceita_verificacao=True,
                foto_perfil="pedidos/fotos/perfil.jpg",
                foto_extra_1="pedidos/fotos/extra-1.jpg",
                foto_extra_2="pedidos/fotos/extra-2.jpg",
                foto_extra_3="pedidos/fotos/extra-3.jpg",
                bi_frente="pedidos/documentos/frente.jpg",
                bi_verso="pedidos/documentos/verso.jpg",
                selfie_com_bi="pedidos/documentos/selfie.jpg",
                status="PENDENTE",
            )
        mail.outbox.clear()

        with self.captureOnCommitCallbacks(execute=True):
            pedido.status = "APROVADO"
            pedido.save(update_fields=["status", "atualizado_em"])

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [pedido.email])
        self.assertIn("aprovado", mail.outbox[0].subject.lower())
        self.assertIn(
            f"https://www.nkata.co.mz/questionario/{pedido.token}/",
            mail.outbox[0].body,
        )
