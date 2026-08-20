from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase

from .models import PreferenciasContaNKATA
from .serializers import PerfilResumoSerializer


class AccountPreferencesApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="preferences-owner",
            email="owner@example.com",
            password="SenhaForte123",
        )
        self.other = User.objects.create_user(
            username="preferences-other",
            email="other@example.com",
            password="SenhaForte123",
        )

    def test_preferences_require_authentication(self):
        response = self.client.get("/api/minha-conta/preferencias/")
        self.assertIn(response.status_code, (401, 403))

    def test_get_creates_safe_defaults_for_current_user(self):
        self.client.force_login(self.owner)

        response = self.client.get("/api/minha-conta/preferencias/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["idioma"], "PT")
        self.assertEqual(response.json()["tema_perfil"], "CLASSICO")
        self.assertEqual(response.json()["fundo_conversa"], "SERENO")
        self.assertTrue(
            PreferenciasContaNKATA.objects.filter(usuario=self.owner).exists()
        )

    def test_patch_updates_only_the_authenticated_users_preferences(self):
        other_preferences = PreferenciasContaNKATA.objects.create(
            usuario=self.other,
            idioma="PT",
            tema_perfil="CLASSICO",
            fundo_conversa="SERENO",
        )
        self.client.force_login(self.owner)

        response = self.client.patch(
            "/api/minha-conta/preferencias/",
            data={
                "idioma": "en",
                "tema_perfil": "areia",
                "fundo_conversa": "botanico",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["idioma"], "EN")
        self.assertEqual(response.json()["tema_perfil"], "AREIA")
        self.assertEqual(response.json()["fundo_conversa"], "BOTANICO")
        owner_preferences = PreferenciasContaNKATA.objects.get(usuario=self.owner)
        self.assertEqual(owner_preferences.tema_perfil, "AREIA")
        other_preferences.refresh_from_db()
        self.assertEqual(other_preferences.tema_perfil, "CLASSICO")

    def test_invalid_option_does_not_change_saved_preferences(self):
        preferences = PreferenciasContaNKATA.objects.create(usuario=self.owner)
        self.client.force_login(self.owner)

        response = self.client.patch(
            "/api/minha-conta/preferencias/",
            data={"tema_perfil": "NEON"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("tema_perfil", response.json()["errors"])
        preferences.refresh_from_db()
        self.assertEqual(preferences.tema_perfil, "CLASSICO")

    def test_profile_serializer_uses_the_owners_selected_theme(self):
        PreferenciasContaNKATA.objects.create(
            usuario=self.owner,
            tema_perfil="NOITE",
        )
        profile = SimpleNamespace(usuario=self.owner)

        theme = PerfilResumoSerializer().get_tema_perfil(profile)

        self.assertEqual(theme, "NOITE")
