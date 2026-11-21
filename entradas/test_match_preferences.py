from django.test import TestCase

from .models import PedidoEntrada, QuestionarioEntrada
from .test_governance_rules import create_member


class MatchPreferencesTests(TestCase):
    def test_questionnaire_validates_and_saves_structured_preferences(self):
        pedido = PedidoEntrada.objects.create(
            nome_completo="Novo Membro", email="new@example.test", telefone="+258840000520",
            cidade="Maputo", idade=28, genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
            status="APROVADO",
        )
        url = f"/api/questionario/{pedido.token}/"
        answers = {
            "disponibilidade": "SIM", "tem_filhos": "NAO", "aceita_pessoa_com_filhos": "SIM",
            "cidade_preferida": "Maputo", "aceita_regras": True,
            "sobre_si": "Gosto de ler e caminhar ao fim da tarde.",
            "o_que_valoriza": "Respeito e boa comunicação.",
            "o_que_nao_aceita": "Falta de respeito.",
            "preferencias": {"ages": [35, 25], "height": 170, "smoking": "never"},
        }
        response = self.client.post(url, answers, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("ages", response.json()["errors"])
        self.assertFalse(QuestionarioEntrada.objects.filter(pedido=pedido).exists())

        answers["preferencias"]["ages"] = None
        response = self.client.post(url, answers, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(pedido.questionario.faixa_etaria_preferida, "Sem preferência")
        self.assertEqual(self.client.get(url).json()["values"]["preferencias"], answers["preferencias"])

    def test_legacy_ages_and_member_visibility_controls(self):
        user, profile = create_member()
        viewer, _ = create_member("viewer@example.test")
        QuestionarioEntrada.objects.create(pedido=profile.pedido, faixa_etaria_preferida="25–35 anos")
        account_url = "/api/minha-conta/"
        detail_url = f"/api/perfis/{profile.pk}/"

        self.client.force_login(user)
        self.assertEqual(self.client.get(account_url).json()["preferencias"]["ages"], [25, 35])
        response = self.client.patch(account_url, {
            "preferencias": {"show_ages": True, "height": 170, "preferred_smoking": "never"},
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.json())

        self.client.force_login(viewer)
        self.assertEqual(self.client.get(detail_url).json()["preferencias"], {"ages": [25, 35]})

        self.client.force_login(user)
        response = self.client.patch(account_url, {
            "preferencias": {"ages": None, "show_details": True},
        }, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.json())
        self.assertIsNone(response.json()["preferencias"]["ages"])

        self.client.force_login(viewer)
        self.assertEqual(self.client.get(detail_url).json()["preferencias"], {"height": 170})

    def test_pet_choices_can_be_shared_without_exposing_the_matching_preference(self):
        user, profile = create_member()
        viewer, _ = create_member("pet-viewer@example.test")
        QuestionarioEntrada.objects.create(pedido=profile.pedido)
        account_url = "/api/minha-conta/"
        detail_url = f"/api/perfis/{profile.pk}/"
        self.client.force_login(user)
        invalid = self.client.patch(account_url, {
            "preferencias": {"pets": ["none", "dog"]},
        }, content_type="application/json")
        self.assertEqual(invalid.status_code, 400)

        preferences = {"pets": ["dog", "cat"], "preferred_pets": "depends"}
        saved = self.client.patch(account_url, {
            "preferencias": preferences,
        }, content_type="application/json")
        self.assertEqual(saved.status_code, 200, saved.json())
        self.assertEqual(saved.json()["preferencias"]["pets"], preferences["pets"])

        self.client.force_login(viewer)
        self.assertNotIn("pets", self.client.get(detail_url).json()["preferencias"])

        self.client.force_login(user)
        self.assertEqual(self.client.patch(account_url, {
            "preferencias": {"show_pets": True},
        }, content_type="application/json").status_code, 200)
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(detail_url).json()["preferencias"], {"pets": ["dog", "cat"]})
