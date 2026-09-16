import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


BASE_DIR = Path(__file__).resolve().parent.parent


class ProductionConfigurationTests(SimpleTestCase):
    maxDiff = None

    def production_env(self, **overrides):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_DEBUG": "False",
                "DJANGO_SECRET_KEY": "test-only-9fG7vQ2mK8xR4sN6pL3wC5aD1hJ0uT9yB7eV2zQ8kM4cX6nP",
                "DJANGO_ALLOWED_HOSTS": "nkata-temporario.example.test",
                "NKATA_FRONTEND_URL": "https://nkata-temporario.example.test",
                "DATABASE_URL": "postgresql://nkata:test@127.0.0.1:5432/nkata",
                "DJANGO_DB_SSL_REQUIRED": "False",
                "REDIS_URL": "redis://127.0.0.1:6379/0",
                "NKATA_STORAGE_BUCKET": "nkata-test-private",
                "CORS_ALLOW_ALL_ORIGINS": "False",
                "CORS_ALLOWED_ORIGINS": "https://nkata-temporario.example.test",
                "CSRF_TRUSTED_ORIGINS": "https://nkata-temporario.example.test",
                "DJANGO_EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "DJANGO_EMAIL_HOST": "smtp.example.test",
                "DJANGO_EMAIL_HOST_USER": "nkata-test",
                "DJANGO_EMAIL_HOST_PASSWORD": "test-only-password",
                "DJANGO_DEFAULT_FROM_EMAIL": "NKATA <no-reply@example.test>",
            }
        )
        env.update(overrides)
        return env

    def import_settings(self, **overrides):
        return subprocess.run(
            [sys.executable, "-c", "import config.settings; print('ok')"],
            cwd=BASE_DIR,
            env=self.production_env(**overrides),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_valid_production_environment_loads(self):
        result = self.import_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_production_rejects_sqlite(self):
        result = self.import_settings(DATABASE_URL="sqlite:///db.sqlite3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deve apontar para PostgreSQL", result.stderr)

    def test_production_rejects_wildcard_host(self):
        result = self.import_settings(DJANGO_ALLOWED_HOSTS="*")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("não pode usar '*'", result.stderr)

    def test_production_rejects_insecure_public_origin(self):
        result = self.import_settings(
            NKATA_FRONTEND_URL="http://nkata-temporario.example.test"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("origem HTTPS pública", result.stderr)
