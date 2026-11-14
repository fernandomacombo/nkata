from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .test_governance_rules import create_member
from .models import MatchPerfil, MensagemMatch, AcessoPlanoNKATA
from .moments_models import MomentoNKATA
from .plan_service import assign_plan, plan_code_for_user
from .payment_service import snapshot


class MomentChatUpdateTests(TestCase):
    def setUp(self):
        self.user, self.profile = create_member()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_phrase_and_appearance_survive_reload(self):
        result = self.client.post('/api/momentos/', {'caption': 'DIA_TRANQUILO', 'theme': 'sand', 'font': 'italic'})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data['text'], 'Um dia tranquilo por aqui.')
        moment = MomentoNKATA.objects.get(pk=result.data['id'])
        self.assertEqual((moment.tema, moment.fonte), ('sand', 'italic'))
        listing = self.client.get('/api/momentos/')
        self.assertEqual(listing.data['results'][0]['theme'], 'sand')

    def test_blank_and_untrusted_styles_rejected(self):
        self.assertEqual(self.client.post('/api/momentos/', {'caption': 'SEM_LEGENDA'}).status_code, 400)
        self.assertEqual(self.client.post('/api/momentos/', {'caption': 'DIA_TRANQUILO', 'theme': 'url(evil)'}).status_code, 400)
        self.assertEqual(MomentoNKATA.objects.count(), 0)

    def test_legacy_caption_field_accepted(self):
        response = self.client.post('/api/momentos/', {'legenda': 'BOAS_ENERGIAS'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'Boas energias para o dia.')

    def test_free_chat_restricts_and_paid_chat_expires(self):
        _, other = create_member('other@nkata.test')
        match = MatchPerfil.objects.create(perfil_1=self.profile, perfil_2=other)
        url = f'/api/minha-conta/matches/{match.id}/conversa/'
        self.assertEqual(self.client.post(url, {'texto': 'Mensagem livre'}).status_code, 403)
        self.assertEqual(MensagemMatch.objects.count(), 0)
        self.assertEqual(self.client.post(url, {'texto': 'Olá, tudo bem?'}).status_code, 201)
        assign_plan(self.user, 'QUINZENAL')
        self.assertEqual(self.client.post(url, {'texto': 'Mensagem livre'}).status_code, 201)
        AcessoPlanoNKATA.objects.filter(usuario=self.user).update(inicio=timezone.now() - timedelta(days=15), fim=timezone.now() - timedelta(seconds=1))
        self.assertEqual(plan_code_for_user(self.user), 'LIVRE')
        self.assertEqual(self.client.post(url, {'texto': 'Mensagem livre'}).status_code, 403)

    def test_fortnight_price_and_term(self):
        self.assertEqual(snapshot('QUINZENAL'), (Decimal('100'), 14, 0))
        before = timezone.now()
        assign_plan(self.user, 'QUINZENAL')
        access = AcessoPlanoNKATA.objects.get(usuario=self.user)
        self.assertAlmostEqual((access.fim-before).total_seconds(), 14*86400, delta=3)
