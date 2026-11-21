from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .launch_promotion import complete_registration_password
from .models import AcessoPlanoNKATA, PromocaoLancamentoNKATA


class LaunchPromotionTests(TestCase):
    def test_last_place_is_granted_once_and_next_account_still_opens(self):
        campaign = PromocaoLancamentoNKATA.objects.create(
            codigo="lancamento-15-dias", vagas_atribuidas=99,
        )
        first = get_user_model().objects.create_user("place-100")
        second = get_user_model().objects.create_user("place-101")

        self.assertEqual(complete_registration_password(first, "first"), (True, True))
        self.assertEqual(complete_registration_password(first, "changed"), (False, False))
        self.assertEqual(complete_registration_password(second, "second"), (True, False))

        campaign.refresh_from_db()
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(campaign.vagas_atribuidas, 100)
        self.assertTrue(first.check_password("first"))
        self.assertTrue(second.check_password("second"))
        self.assertFalse(AcessoPlanoNKATA.objects.filter(usuario=second).exists())

    def test_existing_paid_access_keeps_its_validity(self):
        user = get_user_model().objects.create_user("paid")
        now = timezone.now()
        access = AcessoPlanoNKATA.objects.create(
            usuario=user, plano="PREMIUM", origem="PAYSUITE",
            inicio=now, fim=now + timedelta(days=30),
        )

        self.assertEqual(complete_registration_password(user, "paid-password"), (True, False))
        access.refresh_from_db()
        self.assertEqual(access.plano, "PREMIUM")
        self.assertEqual(access.fim, now + timedelta(days=30))
        self.assertFalse(PromocaoLancamentoNKATA.objects.exists())
