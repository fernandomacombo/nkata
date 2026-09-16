from django.test import SimpleTestCase
from django.urls import resolve

from .plan_service import PLAN_DEFINITIONS
from .posts_api import POST_CAPTIONS
from .posts_models import PublicacaoNKATA, ReacaoPublicacaoNKATA


class PublicationRulesTests(SimpleTestCase):
    def test_publicar_media_exige_plano_pago(self):
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["feed_media_publish"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["feed_media_publish"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["feed_media_publish"])

    def test_feed_continua_visivel_no_plano_livre(self):
        self.assertTrue(PLAN_DEFINITIONS["LIVRE"]["features"]["feed_view"])

    def test_legendas_sao_predefinidas(self):
        values = {item["value"] for item in POST_CAPTIONS}
        self.assertIn("SEM_LEGENDA", values)
        self.assertTrue(all("text" in item for item in POST_CAPTIONS))

    def test_rotas_de_publicacoes_resolvem(self):
        self.assertEqual(resolve("/api/publicacoes/").url_name, "publicacoes")
        self.assertEqual(
            resolve("/api/publicacoes/9/reacoes/").url_name,
            "reacoes_publicacao",
        )

    def test_modelos_nao_criam_comentarios(self):
        field_names = {field.name for field in PublicacaoNKATA._meta.get_fields()}
        self.assertNotIn("comentarios", field_names)
        self.assertEqual(
            ReacaoPublicacaoNKATA._meta.db_table,
            "entradas_reacaopublicacaonkata",
        )
