from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from .admin import SupportTicketAdmin
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

    def test_django_admin_restricts_ticket_access_to_superuser(self):
        User = get_user_model()
        operator = User.objects.create_user(username="staff4", email="staff4@example.org", password="safe-password-123", is_staff=True)
        administrator = User.objects.create_superuser(username="admin4", email="admin4@example.org", password="safe-password-123")
        model_admin = SupportTicketAdmin(SupportTicket, AdminSite())
        request = RequestFactory().get("/admin/helpdesk/supportticket/")
        request.user = operator
        self.assertFalse(model_admin.has_module_permission(request))
        self.assertFalse(model_admin.has_view_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        request.user = administrator
        self.assertTrue(model_admin.has_view_permission(request))
        self.assertTrue(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

    def test_member_email_cannot_be_spoofed_by_form(self):
        member = get_user_model().objects.create_user(
            username="memberemail", email="real@example.org", password="safe-password-123",
        )
        self.client.force_authenticate(user=member)
        response = self.client.post(
            "/api/ajuda/pedidos/",
            {**self.data, "email": "attacker@example.org"}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        ticket = SupportTicket.objects.get()
        self.assertEqual(ticket.email, "real@example.org")
        self.assertEqual(ticket.user, member)

    def test_non_superuser_staff_cannot_reply(self):
        operator = get_user_model().objects.create_user(
            username="helpstaff", email="helpstaff@example.org",
            password="safe-password-123", is_staff=True,
        )
        ticket = SupportTicket.objects.create(
            email="guest@example.org", category="conta",
            subject="Dificuldade de acesso", description="Descrição suficientemente detalhada.",
        )
        self.client.force_authenticate(user=operator)
        with patch("helpdesk.api.send_branded_email") as send:
            response = self.client.post(
                f"/api/ajuda/painel/pedidos/{ticket.pk}/responder/",
                {"body": "Estamos a verificar o problema."}, format="json",
            )
        self.assertEqual(response.status_code, 403)
        send.assert_not_called()
        self.assertFalse(SupportReply.objects.filter(ticket=ticket).exists())

    def test_invalid_reply_status_does_not_send_email(self):
        administrator = get_user_model().objects.create_superuser(
            username="adminstatus", email="adminstatus@example.org",
            password="safe-password-123",
        )
        ticket = SupportTicket.objects.create(
            email="guest@example.org", category="conta",
            subject="Problema no acesso", description="Descrição suficientemente detalhada.",
        )
        self.client.force_authenticate(user=administrator)
        with patch("helpdesk.api.send_branded_email") as send:
            response = self.client.post(
                f"/api/ajuda/painel/pedidos/{ticket.pk}/responder/",
                {"body": "Vamos verificar o assunto.", "status": "falso"}, format="json",
            )
        self.assertEqual(response.status_code, 400)
        send.assert_not_called()

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_reply_generates_real_django_email(self):
        from django.core import mail
        administrator = get_user_model().objects.create_superuser(
            username="adminmail", email="adminmail@example.org",
            password="safe-password-123",
        )
        ticket = SupportTicket.objects.create(
            email="recipient@example.org", category="conta",
            subject="Ajuda para entrar", description="Descrição suficientemente detalhada.",
        )
        self.client.force_authenticate(user=administrator)
        response = self.client.post(
            f"/api/ajuda/painel/pedidos/{ticket.pk}/responder/",
            {"body": "Vamos analisar o seu problema.", "status": "em_analise"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["recipient@example.org"])
        self.assertEqual(SupportReply.objects.filter(ticket=ticket).count(), 1)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "em_analise")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_guest_confirmation_contains_ticket_reference(self):
        from django.core import mail
        response = self.client.post("/api/ajuda/pedidos/", self.data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["guest@example.org"])
        self.assertIn(response.data["id"], mail.outbox[0].body)

    def test_ticket_is_preserved_if_confirmation_email_fails(self):
        with patch("helpdesk.api.send_branded_email", return_value=0):
            response = self.client.post("/api/ajuda/pedidos/", self.data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SupportTicket.objects.filter(pk=response.data["id"]).exists())
