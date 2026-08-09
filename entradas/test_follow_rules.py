from django.test import SimpleTestCase
from django.urls import resolve

from .models import AcaoPerfil


class FollowRulesTests(SimpleTestCase):
    def test_seguir_e_uma_acao_propria(self):
        choices = dict(AcaoPerfil.TIPO_CHOICES)
        self.assertIn("SEGUIR", choices)
        self.assertNotEqual(choices["SEGUIR"], choices["INTERESSE"])

    def test_rota_de_seguir_resolve_para_api_correta(self):
        match = resolve("/api/perfis/7/seguir/")
        self.assertEqual(match.url_name, "alternar_seguir")

    def test_rota_da_lista_privada_resolve_para_api_correta(self):
        match = resolve("/api/minha-conta/a-seguir/")
        self.assertEqual(match.url_name, "perfis_seguidos")

    def test_seguir_nao_e_match_nem_interesse(self):
        self.assertNotEqual("SEGUIR", "INTERESSE")
        self.assertNotEqual("SEGUIR", "MATCH")
