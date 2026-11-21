from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import PedidoEntrada
from .test_governance_rules import create_member


class ProfileNameTests(TestCase):
    def test_account_update_rejects_contacts_and_accepts_names(self):
        member, profile = create_member()
        self.client.force_login(member)
        url = "/api/minha-conta/"
        for name in ("Vivi +258 840 000 001", "Vivi contato@example.test", "Vivi site.example", "Vivi ８４"):
            with self.subTest(name=name):
                response = self.client.patch(url, {"nome_publico": name}, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("nome_publico", response.json())
        profile.refresh_from_db()
        self.assertEqual(profile.nome_publico, "Membro")

        response = self.client.patch(url, {"nome_publico": "Ána-Maria d’Ávila"}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.json())
        profile.refresh_from_db()
        self.assertEqual(profile.nome_publico, "Ána-Maria d’Ávila")

    def test_registration_model_validates_name(self):
        field = PedidoEntrada._meta.get_field("nome_completo")
        with self.assertRaises(ValidationError):
            field.run_validators("Vivi 840000001")

    def test_migration_removes_existing_contacts_from_public_names(self):
        member, profile = create_member()
        profile.nome_publico = "Vivi +258 840 000 001"
        profile.save(update_fields=["nome_publico"])
        member.first_name = "Vivi contacto@example.test"
        member.save(update_fields=["first_name"])

        migration = import_module("entradas.migrations.0034_protect_public_names")
        migration.clean_existing_public_names(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))

        profile.refresh_from_db()
        member.refresh_from_db()
        self.assertEqual(profile.nome_publico, "Vivi")
        self.assertEqual(member.first_name, "Vivi")
