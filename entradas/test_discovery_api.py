from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import AcaoPerfil, QuestionarioEntrada
from .test_governance_rules import create_member


class DiscoveryTests(TestCase):
    def setUp(self):
        self.member, self.profile = create_member()
        self.client.force_login(self.member)

    def test_suggestions_rank_preferences_and_respect_blocks(self):
        QuestionarioEntrada.objects.create(
            pedido=self.profile.pedido,
            cidade_preferida="Mápúto",
            faixa_etaria_preferida="29 a 35 anos",
        )
        _, weaker = create_member("far@example.test")
        weaker.cidade = "Beira"
        weaker.save(update_fields=["cidade"])
        _, preferred = create_member("preferred@example.test")
        blocked_user, _ = create_member("blocked@example.test")
        AcaoPerfil.objects.create(usuario=blocked_user, perfil=self.profile, tipo="BLOQUEIO")
        response = self.client.get("/api/descoberta/sugestoes/")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([item["id"] for item in results], [preferred.pk, weaker.pk])
        self.assertEqual(results[0]["reasons"], ["same_goal", "preferred_city", "preferred_age"])
        self.assertNotIn("email", results[0])
        self.assertIn("no-store", response["Cache-Control"])

    def test_poll_only_shows_totals_after_vote_and_keeps_first_choice(self):
        url = "/api/descoberta/pergunta/"
        today = timezone.localdate()
        response = self.client.get(url)
        self.assertIsNone(response.json()["counts"])
        stale = self.client.post(url, {"date": (today - timedelta(days=1)).isoformat(), "option": 1}, content_type="application/json")
        self.assertEqual(stale.status_code, 409)

        for option in (0, 1):
            response = self.client.post(url, {"date": today.isoformat(), "option": option}, content_type="application/json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["choice"], 0)
            self.assertEqual(response.json()["counts"], [1, 0])

        other, _ = create_member("another-voter@example.test")
        self.client.force_login(other)
        self.assertIsNone(self.client.get(url).json()["counts"])
