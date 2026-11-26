from django.test import SimpleTestCase
from uuid import uuid4
from .moment_credit_service import parse_moment_confirmation, MomentCreditError, PHOTO_COST, VIDEO_COST

class MomentCreditConfirmationTests(SimpleTestCase):
    def test_prices_and_keys(self):
        key = uuid4()
        self.assertEqual(PHOTO_COST, 2)
        self.assertEqual(VIDEO_COST, 5)
        for cost in (0, 2, 5):
            self.assertEqual(parse_moment_confirmation({"key":str(key),"expected_cost":cost}), (key,cost))

    def test_invalid_or_missing_confirmation(self):
        for data in ({}, {"key":"bad","expected_cost":0}, {"key":str(uuid4()),"expected_cost":-1}, {"key":str(uuid4()),"expected_cost":1}):
            with self.assertRaises(MomentCreditError):
                parse_moment_confirmation(data)

from django.test import TestCase, override_settings
from .test_conversations import profile
from .test_profile_gallery_api import image_file, video_file
from .models import EnvioMomentoCreditoNKATA, MovimentoCreditoNKATA
from .moments_models import MomentoNKATA
from .wallet_service import credit_balance, record_movement


@override_settings(NKATA_CREDIT_ONLY_ENABLED=True, NKATA_CREDIT_TRANSITION_ENABLED=True,
                   NKATA_CREDIT_SPENDING_ENABLED=True)
class MomentCreditApiTests(TestCase):
    def setUp(self):
        self.member = profile(77)
        self.user = self.member.usuario
        self.client.force_login(self.user)
        self.url = "/api/momentos/"

    def submit(self, cost, key=None, video=False, **extra):
        return self.client.post(self.url, {"media": video_file() if video else image_file(),
            "key": str(key or uuid4()), "expected_cost": str(cost),
            "caption": "SEM_LEGENDA", "visibilidade": "TODOS", **extra})

    def fund(self):
        record_movement(self.user, key="moment-test", kind="AJUSTE", amount=45,
                        reference="TEST", reason="Saldo de teste")

    def test_verified_member_and_free_photo(self):
        capabilities = self.client.get(self.url).json()["capabilities"]
        self.assertTrue(capabilities["credit_mode"])
        self.assertTrue(capabilities["media_enabled"])
        self.assertEqual(capabilities["moment_offer"]["photo_cost"], 0)
        key = uuid4()
        first = self.submit(0, key)
        self.assertEqual(first.status_code, 202, first.content)
        self.assertEqual(first.json()["moment"]["moderation_status"], "PENDENTE")
        self.assertEqual(self.submit(0, key).status_code, 200)
        self.assertEqual(EnvioMomentoCreditoNKATA.objects.count(), 1)
        self.assertEqual(credit_balance(self.user), 0)
        pk = first.json()["moment"]["id"]
        self.assertEqual(self.client.delete(f"{self.url}{pk}/").status_code, 200)
        self.assertEqual(self.submit(0, key).status_code, 409)
        self.assertEqual(self.submit(0).status_code, 409)
        self.assertEqual(self.submit(2).status_code, 409)

    def test_photo_and_video_charged_once_and_stale_price_rejected(self):
        self.fund()
        self.assertEqual(self.submit(0).status_code, 202)
        key = uuid4()
        second = self.submit(2, key)
        self.assertEqual(second.status_code, 202, second.content)
        self.assertEqual(self.submit(2, key).status_code, 200)
        self.assertEqual(self.submit(2, key, theme="forest").status_code, 409)
        self.assertEqual(self.submit(5, key, video=True).status_code, 409)
        self.assertEqual(self.submit(5, video=True).status_code, 202)
        self.assertEqual(credit_balance(self.user), 38)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(tipo="CONSUMO").count(), 2)
        self.assertEqual(EnvioMomentoCreditoNKATA.objects.count(), 3)

    def test_unverified_cannot_upload_media_but_can_read(self):
        self.member.pedido.identidade_revogada = True
        self.member.pedido.save()
        capabilities = self.client.get(self.url).json()["capabilities"]
        self.assertFalse(capabilities["media_enabled"])
        self.assertTrue(capabilities["identity_required"])
        self.assertEqual(self.submit(0).status_code, 403)
        self.assertFalse(EnvioMomentoCreditoNKATA.objects.exists())

    def test_text_still_free_and_approved(self):
        result = self.client.post(self.url, {"caption": "DIA_TRANQUILO"})
        self.assertEqual(result.status_code, 201, result.content)
        self.assertEqual(result.json()["moderation_status"], "APROVADO")
        self.assertEqual(credit_balance(self.user), 0)
        self.assertFalse(EnvioMomentoCreditoNKATA.objects.exists())

    def test_refund_once_on_rejection_and_no_reapproval(self):
        from .moment_credit_service import moderate_moment
        from .wallet_statement import member_statement
        self.fund()
        response = self.submit(5, video=True)
        self.assertEqual(response.status_code, 202, response.content)
        pk = response.json()["moment"]["id"]
        self.assertEqual(credit_balance(self.user), 40)
        item, refund = moderate_moment(pk, action="reject", note="Rejeitado em teste")
        self.assertEqual(item.moderacao_status, "REJEITADO")
        self.assertEqual(refund.quantidade, 5)
        self.assertEqual(credit_balance(self.user), 45)
        _, repeat = moderate_moment(pk, action="reject", note="Rejeitado em teste")
        self.assertEqual(refund.pk, repeat.pk)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(tipo="ESTORNO").count(), 1)
        with self.assertRaises(MomentCreditError):
            moderate_moment(pk, action="approve")
        payload = self.client.get(self.url).json()["review_items"][0]
        self.assertEqual(payload["refunded_credits"], 5)
        statement = member_statement(self.user)
        self.assertEqual(statement["summary"]["refunded"], 5)
        self.assertEqual(next(row for row in statement["breakdown"] if row["code"] == "moments")["credits"], 5)

    def test_free_rejection_does_not_mint_credits(self):
        from .moment_credit_service import moderate_moment
        response = self.submit(0)
        self.assertEqual(response.status_code, 202, response.content)
        _, refund = moderate_moment(response.json()["moment"]["id"], action="reject", note="Teste")
        self.assertIsNone(refund)
        self.assertEqual(credit_balance(self.user), 0)
        self.assertEqual(self.client.get(self.url).json()["capabilities"]["moment_offer"]["photo_cost"], 2)

    def test_approval_does_not_extend_twice(self):
        from .moment_credit_service import moderate_moment
        self.fund()
        response = self.submit(5, video=True)
        self.assertEqual(response.status_code, 202, response.content)
        pk = response.json()["moment"]["id"]
        first, _ = moderate_moment(pk, action="approve")
        second, _ = moderate_moment(pk, action="approve")
        self.assertEqual(first.expira_em, second.expira_em)
        self.assertEqual(credit_balance(self.user), 40)

    def test_audit_matches_moment_receipt_and_refund(self):
        from io import StringIO
        from django.core.management import call_command, CommandError
        from unittest.mock import patch
        from .moment_credit_service import moderate_moment
        self.fund()
        response = self.submit(5, video=True)
        self.assertEqual(response.status_code, 202, response.content)
        moderate_moment(response.json()["moment"]["id"], action="reject", note="Teste")
        with patch("entradas.management.commands.auditar_creditos.connection.vendor", "sqlite"):
            output = StringIO()
            call_command("auditar_creditos", stdout=output, stderr=StringIO())
            self.assertIn("ocorrências: 0", output.getvalue())
            record_movement(self.user, key=f"moment:{uuid4()}", kind="CONSUMO", amount=-2,
                            reference="TEST", reason="Movimento órfão de teste")
            errors = StringIO()
            with self.assertRaises(CommandError):
                call_command("auditar_creditos", stdout=StringIO(), stderr=errors)
            self.assertIn("MOMENTO_MOVIMENTO_SEM_RECIBO", errors.getvalue())
            self.assertEqual(credit_balance(self.user), 43)
