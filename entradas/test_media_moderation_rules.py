from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .content_moderation_admin import automatic_review_panel
from .content_moderation_models import AnaliseAutomaticaConteudoNKATA
from .content_moderation_service import (
    highest_risk,
    moderation_provider_label,
    risk_from_moderation_result,
    status_from_risk,
)
from .media_inspection_service import (
    contact_signals_from_text,
    merge_inspection_signals,
    risk_from_inspection_signals,
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

    @override_settings(
        NKATA_MEDIA_MODERATION_PROVIDER="manual",
        NKATA_MEDIA_VISION_SCAN_ENABLED=False,
    )
    def test_provider_manual_identifica_open_cv_e_revisao_humana(self):
        label = moderation_provider_label().lower()
        self.assertIn("opencv", label)
        self.assertIn("revisão humana", label)

    def test_admin_sem_analise_nao_quebra_no_django_6(self):
        with patch("entradas.content_moderation_admin.analysis_for", return_value=None):
            html = str(automatic_review_panel("PUBLICACAO", 999999))
        self.assertIn("Sem registo automático", html)
        self.assertIn("revisão humana", html)

    def test_contactos_mocambicanos_email_handle_e_url_sao_reconhecidos(self):
        signals = contact_signals_from_text(
            "WhatsApp 876598403, email pessoa@example.com, @perfil e https://example.com"
        )
        self.assertTrue(signals["contact_phone"])
        self.assertTrue(signals["contact_email"])
        self.assertTrue(signals["contact_username"])
        self.assertTrue(signals["contact_url"])

    def test_qr_ou_contacto_e_risco_alto(self):
        self.assertEqual(
            risk_from_inspection_signals({"qr_code": True}),
            "ALTO",
        )
        self.assertEqual(
            risk_from_inspection_signals({"contact_phone": True}),
            "ALTO",
        )

    def test_servicos_sexuais_e_risco_critico(self):
        self.assertEqual(
            risk_from_inspection_signals({"sexual_services_solicitation": True}),
            "CRITICO",
        )

    def test_sinais_locais_e_visuais_sao_combinados_sem_apagar_alertas(self):
        merged = merge_inspection_signals(
            {"qr_code": True, "contact_phone": False},
            {"contact_phone": True, "advertising_or_sales": True},
        )
        self.assertTrue(merged["qr_code"])
        self.assertTrue(merged["contact_phone"])
        self.assertTrue(merged["advertising_or_sales"])

    def test_maior_risco_prevalece(self):
        self.assertEqual(highest_risk("BAIXO", "ALTO", "MEDIO"), "ALTO")
        self.assertEqual(highest_risk("ALTO", "CRITICO"), "CRITICO")
