from django.core import mail
from django.test import SimpleTestCase, override_settings

from .branded_email import render_email_html, send_branded_email


class BrandedEmailTests(SimpleTestCase):
    def test_html_escapes_user_content_and_rejects_unsafe_link(self):
        html = render_email_html(
            title="Olá <script>", greeting="Marta & João",
            paragraphs=["<strong>não interpretar</strong>"],
            action_label="Abrir", action_url="javascript:alert(1)",
        )
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Marta &amp; João", html)
        self.assertNotIn('<script>', html)
        self.assertNotIn("javascript:", html)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="NKATA <notificacoes@nkata.date>",
    )
    def test_email_has_plain_text_and_html_alternative(self):
        send_branded_email(
            subject="Recuperar acesso",
            body="Este é o conteúdo em texto simples.",
            recipient="exemplo@example.com", title="Nova palavra-passe",
            greeting="Olá Marta", paragraphs=["Pedido recebido."],
            action_label="Continuar",
            action_url="https://www.nkata.date/recuperar-senha/",
        )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("texto simples", message.body)
        self.assertEqual(message.alternatives[0][1], "text/html")
        self.assertIn("https://www.nkata.date/recuperar-senha/", message.alternatives[0][0])
