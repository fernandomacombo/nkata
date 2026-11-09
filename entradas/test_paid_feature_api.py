from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .call_api import api_chamada_match
from .chat_media_api import api_audios_match
from .posts_api import api_publicacoes
from .plan_service import assign_plan, public_plan_catalog


class PaidFeatureApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="free-member")
        self.factory = APIRequestFactory()

    def request(self, data):
        request = self.factory.post("/api/", data, format="json")
        force_authenticate(request, user=self.user)
        return request

    def test_free_cannot_send_audio_even_if_client_claims_premium(self):
        with patch("entradas.chat_media_api._match_do_utilizador", return_value=object()):
            response = api_audios_match(self.request({"plan": "PREMIUM"}), 1)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "paid_plan_required_for_chat_audio")

    def test_free_cannot_start_audio_or_video_calls(self):
        for call_type in ("AUDIO", "VIDEO"):
            with self.subTest(call_type=call_type), patch(
                "entradas.call_api._match_do_utilizador", return_value=object()
            ):
                response = api_chamada_match(self.request({"action": "start", "type": call_type}), 1)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.data["code"], "paid_plan_required_for_call")

    def test_free_cannot_publish_media(self):
        with patch("entradas.posts_api._perfil_do_utilizador", return_value=SimpleNamespace(status="ATIVO")):
            response = api_publicacoes(self.request({"plan": "PREMIUM"}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "paid_plan_required_for_publication")

    def test_audio_access_is_revoked_when_plan_returns_to_free(self):
        with patch("entradas.chat_media_api._match_do_utilizador", return_value=object()):
            assign_plan(self.user, "ESSENCIAL")
            response = api_audios_match(self.request({}), 1)
            self.assertEqual(response.status_code, 400)  # Paid gate passed; upload absent.
            assign_plan(self.user, "LIVRE")
            response = api_audios_match(self.request({}), 1)
            self.assertEqual(response.status_code, 403)

    def test_catalog_does_not_advertise_unimplemented_features(self):
        for plan in public_plan_catalog():
            self.assertFalse(plan["features"]["advanced_filters"])
            self.assertFalse(plan["features"]["priority_discovery"])
