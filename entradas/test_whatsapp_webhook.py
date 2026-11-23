import hmac

from django.test import Client, SimpleTestCase, override_settings


@override_settings(
    NKATA_WHATSAPP_VERIFY_TOKEN="test-verify-token",
    NKATA_WHATSAPP_APP_SECRET="test-app-secret",
)
class WhatsAppWebhookTests(SimpleTestCase):
    url = "/api/whatsapp/webhook/"

    def test_meta_verification_returns_exact_challenge(self):
        response = self.client.get(self.url, {
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "000123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"000123")

    def test_wrong_token_is_rejected(self):
        self.assertEqual(self.client.get(self.url, {
            "hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "123",
        }).status_code, 403)

    @override_settings(NKATA_WHATSAPP_APP_SECRET="")
    def test_callback_requires_configuration(self):
        self.assertEqual(self.client.get(self.url).status_code, 503)

    def test_post_requires_signature_over_exact_body(self):
        client = Client(enforce_csrf_checks=True)
        payload = b'{"object":"whatsapp_business_account","entry":[]}'
        headers = {"X-Hub-Signature-256": "sha256=" + hmac.digest(
            b"test-app-secret", payload, "sha256",
        ).hex()}
        self.assertEqual(client.post(self.url, payload, content_type="application/json").status_code, 403)
        self.assertEqual(client.post(
            self.url, payload + b" ", content_type="application/json", headers=headers,
        ).status_code, 403)
        self.assertEqual(client.post(
            self.url, payload, content_type="application/json", headers=headers,
        ).status_code, 200)
