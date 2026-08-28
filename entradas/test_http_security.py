from django.test import Client, TestCase, override_settings


class HttpSecurityTests(TestCase):
    @override_settings(
        ALLOWED_HOSTS=["nkata-temporario.example.test"],
        SECURE_HSTS_SECONDS=3600,
        SECURE_SSL_REDIRECT=True,
    )
    def test_https_response_has_security_headers(self):
        response = self.client.get(
            "/",
            secure=True,
            HTTP_HOST="nkata-temporario.example.test",
        )

        self.assertEqual(response.status_code, 200)
        for header in (
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
        ):
            self.assertIn(header, response.headers)

    @override_settings(
        ALLOWED_HOSTS=["nkata-temporario.example.test"],
        SECURE_SSL_REDIRECT=True,
    )
    def test_http_redirects_to_https(self):
        response = self.client.get(
            "/",
            HTTP_HOST="nkata-temporario.example.test",
        )
        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response.headers["Location"],
            "https://nkata-temporario.example.test/",
        )

    @override_settings(ALLOWED_HOSTS=["nkata-temporario.example.test"])
    def test_unknown_host_is_rejected(self):
        client = Client(raise_request_exception=False)
        response = client.get("/", secure=True, HTTP_HOST="atacante.example.test")
        self.assertEqual(response.status_code, 400)

    def test_login_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        session_response = client.get("/api/session/")
        self.assertEqual(session_response.status_code, 200)
        csrf_token = client.cookies["csrftoken"].value

        without_token = client.post(
            "/api/auth/login/",
            data={"email": "ninguém@example.com", "password": "incorreta"},
            content_type="application/json",
        )
        self.assertEqual(without_token.status_code, 403)

        with_token = client.post(
            "/api/auth/login/",
            data={"email": "ninguém@example.com", "password": "incorreta"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(with_token.status_code, 400)
