from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .content_moderation_admin import automatic_review_panel
from .content_moderation_models import AnaliseAutomaticaConteudoNKATA
from .content_moderation_service import (
    moderation_provider_label,
    risk_from_moderation_result,
    status_from_risk,
)


class MediaModerationRulesTests(SimpleTestCase):
    def test_sexual_minors_e_risco_critico(self):
        risk = risk_from_moderation_result({
            "flagged": True,
            "categories": {"sexual/minors": True, "sexual": True},
        })
        self.assertEqual(risk, "CRITICO")

    def test_sexual_ou_violencia_grafica_e_risco_alto(self):
        self.assertEqual(
            risk_from_moderation_result({
                "flagged": True,
                "categories": {"sexual": True},
            }),
            "ALTO",
        )
        self.assertEqual(
            risk_from_moderation_result({
                "flagged": True,
                "categories": {"violence/graphic": True},
            }),
            "ALTO",
        )

    def test_conteudo_nao_sinalizado_e_baixo_risco_mas_nao_aprovado(self):
        risk = risk_from_moderation_result({
            "flagged": False,
            "categories": {"sexual": False, "violence": False},
        })
        self.assertEqual(risk, "BAIXO")
        self.assertEqual(status_from_risk(risk), "BAIXO_RISCO")
        self.assertNotEqual(status_from_risk(risk), "APROVADO")

    def test_modelo_tem_decisao_humana_separada_do_risco(self):
        human_choices = dict(AnaliseAutomaticaConteudoNKATA.HUMAN_CHOICES)
        self.assertIn("APROVADO", human_choices)
        self.assertIn("REJEITADO", human_choices)
        self.assertIn("GRAVE", human_choices)
        self.assertNotIn("BAIXO", human_choices)

    @override_settings(NKATA_MEDIA_MODERATION_PROVIDER="manual")
    def test_provider_manual_e_explicitamente_identificado(self):
        self.assertIn("sem motor externo", moderation_provider_label().lower())

    def test_admin_sem_analise_nao_quebra_no_django_6(self):
        with patch("entradas.content_moderation_admin.analysis_for", return_value=None):
            html = str(automatic_review_panel("PUBLICACAO", 999999))
        self.assertIn("Sem registo automático", html)
        self.assertIn("revisão humana", html)
