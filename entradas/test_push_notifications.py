from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .notification_models import PushSubscriptionNKATA


class PushNotificationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="push-member",
            email="push@example.com",
            password="SenhaForte123",
        )
        self.client.force_login(self.user)

    @override_settings(
        NKATA_WEBPUSH_PUBLIC_KEY="",
        NKATA_WEBPUSH_PRIVATE_KEY="",
    )
    def test_config_explicita_quando_push_ainda_nao_foi_configurado(self):
        response = self.client.get("/api/minha-conta/push/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["supported"])
        self.assertEqual(response.json()["public_key"], "")

    @override_settings(
        NKATA_WEBPUSH_PUBLIC_KEY="public-test-key",
        NKATA_WEBPUSH_PRIVATE_KEY="private-test-key",
        NKATA_WEBPUSH_SUBJECT="mailto:test@example.com",
    )
    def test_membro_regista_e_remove_subscricao_do_proprio_dispositivo(self):
        payload = {
            "endpoint": "https://push.example.com/subscriptions/abc123",
            "keys": {"p256dh": "p256dh-test", "auth": "auth-test"},
        }

        created = self.client.post(
            "/api/minha-conta/push/",
            payload,
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200)
        self.assertTrue(created.json()["subscribed"])
        subscription = PushSubscriptionNKATA.objects.get(destinatario=self.user)
        self.assertTrue(subscription.ativa)

        removed = self.client.delete(
            "/api/minha-conta/push/",
            {"endpoint": payload["endpoint"]},
            content_type="application/json",
        )
        self.assertEqual(removed.status_code, 200)
        subscription.refresh_from_db()
        self.assertFalse(subscription.ativa)

    def test_push_exige_sessao_iniciada(self):
        self.client.logout()
        response = self.client.get("/api/minha-conta/push/")
        self.assertIn(response.status_code, {401, 403})
