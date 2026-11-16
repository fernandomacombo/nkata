from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import SupportTicket


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
