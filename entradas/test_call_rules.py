from types import SimpleNamespace

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from .call_api import CALL_RING_TIMEOUT_SECONDS, MAX_SIGNAL_PAYLOAD_CHARS
from .call_models import ChamadaMatchNKATA, SinalChamadaNKATA
from .plan_service import PLAN_DEFINITIONS
from .webrtc_config_api import api_webrtc_readiness


class CallRulesTests(SimpleTestCase):
    def test_call_models_remain_isolated_from_migrations(self):
        self.assertFalse(ChamadaMatchNKATA._meta.managed)
        self.assertFalse(SinalChamadaNKATA._meta.managed)
        self.assertEqual(
            ChamadaMatchNKATA._meta.db_table,
            "entradas_chamadamatchnkata",
        )
        self.assertEqual(
            SinalChamadaNKATA._meta.db_table,
            "entradas_sinalchamadankata",
        )

    def test_calls_are_paid_features(self):
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["chat_audio"])
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["chat_video"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["chat_audio"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["chat_video"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["chat_audio"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["chat_video"])

    def test_call_route_is_scoped_to_match(self):
        self.assertEqual(
            reverse("entradas_api:chamada_match", kwargs={"match_id": 9}),
            "/api/minha-conta/matches/9/call/",
        )

    def test_incoming_call_route_is_account_scoped(self):
        self.assertEqual(
            reverse("entradas_api:chamada_recebida"),
            "/api/minha-conta/chamadas/entrada/",
        )

    def test_webrtc_readiness_route_is_account_scoped(self):
        self.assertEqual(
            reverse("entradas_api:webrtc_readiness"),
            "/api/minha-conta/webrtc/readiness/",
        )

    def test_default_stun_configuration_uses_stun_urls_only(self):
        self.assertTrue(settings.NKATA_WEBRTC_STUN_URLS)
        self.assertTrue(
            all(
                str(url).startswith(("stun:", "stuns:"))
                for url in settings.NKATA_WEBRTC_STUN_URLS
            )
        )

    @override_settings(
        NKATA_WEBRTC_STUN_URLS=["stun:example.invalid:3478"],
        NKATA_WEBRTC_TURN_URLS=["turn:example.invalid:3478"],
        NKATA_WEBRTC_TURN_USERNAME="segredo-usuario",
        NKATA_WEBRTC_TURN_CREDENTIAL="segredo-credencial",
    )
    def test_readiness_does_not_expose_turn_credentials(self):
        request = APIRequestFactory().get("/api/minha-conta/webrtc/readiness/")
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
        response = api_webrtc_readiness(request)

        self.assertTrue(response.data["stun_configured"])
        self.assertTrue(response.data["turn_configured"])
        rendered = str(response.data)
        self.assertNotIn("segredo-usuario", rendered)
        self.assertNotIn("segredo-credencial", rendered)

    def test_signaling_payload_has_conservative_limit(self):
        self.assertGreaterEqual(MAX_SIGNAL_PAYLOAD_CHARS, 32768)
        self.assertLessEqual(MAX_SIGNAL_PAYLOAD_CHARS, 131072)

    def test_unanswered_call_expires(self):
        self.assertGreaterEqual(CALL_RING_TIMEOUT_SECONDS, 30)
        self.assertLessEqual(CALL_RING_TIMEOUT_SECONDS, 90)

    def test_call_metadata_does_not_store_audio_or_video_recordings(self):
        field_names = {field.name for field in ChamadaMatchNKATA._meta.fields}
        for forbidden in {"audio", "video", "ficheiro", "file", "gravacao", "recording", "sdp", "ice"}:
            self.assertNotIn(forbidden, field_names)
        self.assertIn("tipo", field_names)
        self.assertIn("estado", field_names)
