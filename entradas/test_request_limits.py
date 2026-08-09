from django.test import SimpleTestCase, override_settings


class RequestBodyLimitTests(SimpleTestCase):
    @override_settings(NKATA_MAX_REQUEST_BODY_SIZE=100)
    def test_oversized_api_request_is_rejected_before_view(self):
        response = self.client.post(
            "/api/auth/login/",
            data=b"{}",
            content_type="application/json",
            CONTENT_LENGTH="101",
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("tamanho máximo", response.json()["detail"])
