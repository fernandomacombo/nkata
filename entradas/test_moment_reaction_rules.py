from django.test import SimpleTestCase

from .moment_reaction_service import REACTION_OPTIONS
from .moments_models import ReacaoMomentoNKATA
from .notification_models import NotificacaoNKATA


class MomentReactionRulesTests(SimpleTestCase):
    def test_reacoes_sao_apenas_as_tres_predefinidas(self):
        self.assertEqual(
            [item["value"] for item in REACTION_OPTIONS],
            ["CORACAO", "FLOR", "APLAUSO"],
        )

    def test_reacoes_usam_icones_semanticos_distintos(self):
        icons = [item["icon"] for item in REACTION_OPTIONS]
        self.assertEqual(len(icons), len(set(icons)))
        self.assertEqual(icons, ["heart", "flower", "sparkles"])

    def test_existe_apenas_uma_reacao_por_utilizador_e_momento(self):
        constraints = ReacaoMomentoNKATA._meta.constraints
        fields = [tuple(constraint.fields) for constraint in constraints]
        self.assertIn(("momento", "usuario"), fields)

    def test_notificacao_de_momento_tem_tipo_proprio(self):
        choices = dict(NotificacaoNKATA.TIPO_CHOICES)
        self.assertIn("MOMENTO", choices)
        self.assertNotEqual(choices["MOMENTO"], choices["SINAL"])
