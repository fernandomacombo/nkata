from django.test import SimpleTestCase, override_settings

from .infrastructure_health import infrastructure_configuration


class InfrastructureStatusTests(SimpleTestCase):
    @override_settings(
        NKATA_WEBRTC_TURN_URLS=[],
        NKATA_WEBRTC_TURN_SHARED_SECRET="",
        NKATA_WEBRTC_TURN_USERNAME="",
        NKATA_WEBRTC_TURN_CREDENTIAL="",
        NKATA_MEDIA_MODERATION_PROVIDER="manual",
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        NKATA_PAYMENTS_ENABLED=False,
    )
    def test_unconfigured_services_are_not_reported_as_healthy(self):
        value = infrastructure_configuration()
        self.assertFalse(value["turn_configured"])
        self.assertFalse(value["moderation_automatic"])
        self.assertEqual(value["moderation_mode"], "Revisão humana")
        self.assertFalse(value["email_configured"])
        self.assertFalse(value["payments_configured"])

    @override_settings(
        NKATA_WEBRTC_TURN_URLS=["turn:turn.example.org:3478"],
        NKATA_WEBRTC_TURN_SHARED_SECRET="example-only",
        NKATA_MEDIA_MODERATION_PROVIDER="openai",
        EMAIL_BACKEND="entradas.email_backend.ZohoAPIEmailBackend",
        NKATA_ZOHO_API_KEY="fake-test-key",
        NKATA_PAYMENTS_ENABLED=True,
        NKATA_PAYSUITE_TOKEN="fake-test-token",
        NKATA_PAYSUITE_WEBHOOK_SECRET="fake-test-signature",
    )
    def test_configured_services_are_not_reported_as_live(self):
        value = infrastructure_configuration()
        self.assertTrue(value["turn_configured"])
        self.assertIn("não", value["turn_label"].lower())
        self.assertTrue(value["moderation_automatic"])
        self.assertTrue(value["email_configured"])
        self.assertIn("não testado", value["email_label"].lower())
        self.assertTrue(value["payments_configured"])
        self.assertIn("não testadas", value["payments_label"].lower())
        self.assertNotIn("fake-test", str(value))

    @override_settings(
        NKATA_WEBRTC_TURN_URLS=["turn:turn.example.org:3478"],
        NKATA_WEBRTC_TURN_SHARED_SECRET="",
        NKATA_WEBRTC_TURN_USERNAME="",
        NKATA_WEBRTC_TURN_CREDENTIAL="",
    )
    def test_turn_requires_credentials_and_url(self):
        self.assertFalse(infrastructure_configuration()["turn_configured"])
