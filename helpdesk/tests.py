from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import SupportTicket, SupportReply


@override_settings(REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"]})
class SupportTicketTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.data = {"email": "guest@example.org", "category": "conta", "subject": "Não consigo entrar", "description": "Não consigo entrar na minha conta desde ontem."}

    def test_guest_can_open_ticket_without_exposing_history(self):
        response = self.client.post("/api/ajuda/pedidos/", self.data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SupportTicket.objects.count(), 1)
        self.assertEqual(self.client.get("/api/ajuda/pedidos/").status_code, 401)

    def test_invalid_category_is_rejected(self):
        response = self.client.post("/api/ajuda/pedidos/", {**self.data, "category": "admin"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_member_only_sees_own_tickets(self):
        User = get_user_model()
        a = User.objects.create_user(username="a", email="a@example.org", password="safe-password-123")
        b = User.objects.create_user(username="b", email="b@example.org", password="safe-password-123")
        SupportTicket.objects.create(user=a, email=a.email, category="conta", subject="Problema conta", description="Descrição suficientemente longa.")
        SupportTicket.objects.create(user=b, email=b.email, category="conta", subject="Problema conta B", description="Descrição suficientemente longa.")
        self.client.force_authenticate(user=a)
        response = self.client.get("/api/ajuda/pedidos/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_non_admin_cannot_read_support_inbox(self):
        user = get_user_model().objects.create_user(username="member", email="member@example.org", password="safe-password-123")
        self.client.force_authenticate(user=user)
        self.assertEqual(self.client.get("/api/ajuda/painel/pedidos/").status_code, 403)

    def test_superuser_can_reply_and_member_sees_response(self):
        User = get_user_model()
        member = User.objects.create_user(username="member2", email="member2@example.org", password="safe-password-123")
        administrator = User.objects.create_superuser(username="nkataadmin", email="admin@example.org", password="safe-password-123")
        ticket = SupportTicket.objects.create(user=member, email=member.email, category="conta", subject="Problema de acesso", description="Descrição do problema suficientemente longa.")
        self.client.force_authenticate(user=administrator)
        with patch("helpdesk.api.send_branded_email", return_value=1) as mail:
            response = self.client.post(f"/api/ajuda/painel/pedidos/{ticket.pk}/responder/", {"body": "Vamos analisar a sua conta."}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SupportReply.objects.filter(ticket=ticket).count(), 1)
        mail.assert_called_once()
        self.client.force_authenticate(user=member)
        response = self.client.get("/api/ajuda/pedidos/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"][0]["replies"]), 1)

    def test_failed_email_does_not_record_reply(self):
        User = get_user_model()
        administrator = User.objects.create_superuser(username="admin3", email="admin3@example.org", password="safe-password-123")
        ticket = SupportTicket.objects.create(email="guest@example.org", category="conta", subject="Erro de acesso", description="Descrição do problema suficientemente longa.")
        self.client.force_authenticate(user=administrator)
        with patch("helpdesk.api.send_branded_email", side_effect=RuntimeError("email service failed")):
            response = self.client.post(f"/api/ajuda/painel/pedidos/{ticket.pk}/responder/", {"body": "Estamos a ajudar com este assunto."}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(SupportReply.objects.count(), 0)
