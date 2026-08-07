from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .moments_api import CAPTION_BY_CODE, MOMENT_CAPTIONS
from .moments_models import MOMENT_LIFETIME_HOURS, MomentoNKATA, moment_expires_at
from .plan_service import PLAN_DEFINITIONS


class MomentRulesTests(SimpleTestCase):
    def test_momento_dura_24_horas(self):
        before = timezone.now() + timedelta(hours=24) - timedelta(seconds=2)
        expires = moment_expires_at()
        after = timezone.now() + timedelta(hours=24) + timedelta(seconds=2)

        self.assertEqual(MOMENT_LIFETIME_HOURS, 24)
        self.assertGreaterEqual(expires, before)
        self.assertLessEqual(expires, after)

    def test_frase_predefinida_e_permitida_em_todos_os_planos(self):
        for plan in PLAN_DEFINITIONS.values():
            self.assertTrue(plan["features"]["status_text"])

    def test_media_de_momento_exige_plano_pago(self):
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["status_media"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["status_media"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["status_media"])

    def test_momentos_usam_apenas_frases_controladas(self):
        self.assertGreater(len(MOMENT_CAPTIONS), 1)
        self.assertIn("SEM_LEGENDA", CAPTION_BY_CODE)
        self.assertNotIn("MEU_TEXTO_LIVRE", CAPTION_BY_CODE)

    def test_media_nova_comeca_pendente_de_moderacao(self):
        field = MomentoNKATA._meta.get_field("moderacao_status")
        self.assertEqual(field.default, "PENDENTE")
        self.assertEqual(
            {choice[0] for choice in field.choices},
            {"PENDENTE", "APROVADO", "REJEITADO"},
        )
