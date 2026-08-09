from django.test import SimpleTestCase
from django.urls import resolve

from .post_safety_models import DenunciaPublicacaoNKATA, OcultacaoPublicacaoNKATA


class PostSafetyRulesTests(SimpleTestCase):
    def test_motivos_de_denuncia_sao_predefinidos(self):
        reasons = dict(DenunciaPublicacaoNKATA.MOTIVO_CHOICES)
        self.assertEqual(len(reasons), 6)
        self.assertIn("NUDEZ_SEXUAL", reasons)
        self.assertIn("SERVICOS_SEXUAIS", reasons)
        self.assertIn("CONTACTOS_PUBLICIDADE", reasons)

    def test_denuncia_nao_tem_campo_de_texto_livre(self):
        field_names = {field.name for field in DenunciaPublicacaoNKATA._meta.fields}
        self.assertNotIn("texto", field_names)
        self.assertNotIn("comentario", field_names)
        self.assertNotIn("descricao", field_names)

    def test_denuncia_e_unica_por_publicacao_e_utilizador(self):
        constraints = DenunciaPublicacaoNKATA._meta.constraints
        self.assertTrue(any(
            set(constraint.fields) == {"publicacao", "denunciante"}
            for constraint in constraints
        ))

    def test_ocultacao_e_unica_por_publicacao_e_utilizador(self):
        constraints = OcultacaoPublicacaoNKATA._meta.constraints
        self.assertTrue(any(
            set(constraint.fields) == {"publicacao", "usuario"}
            for constraint in constraints
        ))

    def test_rotas_de_seguranca_resolvem(self):
        hide_match = resolve("/api/publicacoes/7/ocultar/")
        report_match = resolve("/api/publicacoes/7/denunciar/")
        self.assertEqual(hide_match.url_name, "ocultar_publicacao")
        self.assertEqual(report_match.url_name, "denunciar_publicacao")
