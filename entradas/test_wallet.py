from django.test import TestCase
from django.contrib.auth import get_user_model
from .test_conversations import profile
from .models import CarteiraNKATA, MovimentoCreditoNKATA
from .wallet_service import record_movement, wallet_snapshot, reconcile_balance, grant_welcome_credits, WalletError


class WalletTests(TestCase):
    def setUp(self):
        self.a, self.b = profile(90).usuario, profile(91).usuario

    def move(self, key="pay:1", amount=50, kind="RECARGA"):
        return record_movement(self.a, key=key, amount=amount, kind=kind, reference=key, reason="Teste financeiro")

    def test_idempotent_credit_and_debit(self):
        first = self.move()
        self.assertEqual(self.move().pk, first.pk)
        self.move("signal:1", -2, "CONSUMO")
        self.assertEqual(wallet_snapshot(self.a)["saldo"], 48)
        self.assertEqual(MovimentoCreditoNKATA.objects.count(), 2)
        self.assertTrue(reconcile_balance(CarteiraNKATA.objects.get(usuario=self.a))["consistente"])

    def test_conflicting_retry_and_insufficient_balance(self):
        self.move()
        with self.assertRaises(WalletError):
            self.move(amount=100)
        with self.assertRaises(WalletError):
            self.move("too-much", -51, "CONSUMO")
        self.assertEqual(wallet_snapshot(self.a)["saldo"], 50)
        self.assertEqual(MovimentoCreditoNKATA.objects.count(), 1)

    def test_transaction_immutable_via_instance(self):
        movement = self.move()
        movement.quantidade = 100
        with self.assertRaises(ValueError):
            movement.save()
        with self.assertRaises(ValueError):
            movement.delete()

    def test_own_wallet_read_only(self):
        self.move()
        self.client.force_login(self.b)
        url = "/api/minha-conta/carteira/"
        response = self.client.get(url + f"?usuario={self.a.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["saldo"], 0)
        self.assertEqual(self.client.post(url, {"saldo": 10000}).status_code, 405)
        self.assertFalse(CarteiraNKATA.objects.filter(usuario=self.b).exists())

    def test_no_welcome_without_actual_verification(self):
        with self.assertRaises(WalletError):
            grant_welcome_credits(self.a)
        self.assertFalse(CarteiraNKATA.objects.filter(usuario=self.a).exists())

    def test_admin_has_no_member_wallet(self):
        admin = get_user_model().objects.create_user("wallet-admin", is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/api/minha-conta/carteira/").status_code, 403)


    def test_credit_chat_pass_is_idempotent_global_and_expires(self):
        from uuid import uuid4
        from datetime import timedelta
        from django.utils import timezone
        from .models import AcessoChatCreditoNKATA
        from .plan_service import plan_for_user
        from .wallet_service import unlock_chat
        self.move()
        key = uuid4()
        with self.settings(NKATA_CREDIT_SPENDING_ENABLED=True):
            access, charged = unlock_chat(self.a, key=key, expected_cost=10)
            self.assertTrue(charged)
            self.assertEqual(access.fim-access.inicio, timedelta(hours=24))
            self.assertFalse(unlock_chat(self.a, key=key, expected_cost=10)[1])
            self.assertFalse(unlock_chat(self.a, key=uuid4(), expected_cost=10)[1])
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 40)
            self.assertTrue(plan_for_user(self.a)["features"]["chat_text"])
            self.assertFalse(plan_for_user(self.a)["features"]["chat_audio"])
            AcessoChatCreditoNKATA.objects.filter(pk=access.pk).update(inicio=timezone.now()-timedelta(days=2), fim=timezone.now()-timedelta(days=1))
            self.assertFalse(plan_for_user(self.a)["features"]["chat_text"])
            self.assertFalse(unlock_chat(self.a, key=key, expected_cost=10)[1])
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 40)


    def test_signal_cost_requires_confirmation_and_charges_once(self):
        from .models import AcaoPerfil, Conversa
        self.move()
        self.client.force_login(self.a)
        url = f"/api/perfis/{self.b.perfil_nkata.pk}/sinais/"
        with self.settings(NKATA_CREDIT_SPENDING_ENABLED=True):
            self.assertEqual(self.client.post(url, {"tipo": "FLOR", "expected_cost": 1}, content_type="application/json").status_code, 409)
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 50)
            self.assertEqual(self.client.post(url, {"tipo": "FLOR", "expected_cost": 2}, content_type="application/json").status_code, 201)
            self.assertEqual(self.client.post(url, {"tipo": "FLOR", "expected_cost": 2}, content_type="application/json").status_code, 409)
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 48)
            self.assertEqual(AcaoPerfil.objects.filter(usuario=self.a, tipo="SINAL_FLOR").count(), 1)
            self.assertFalse(Conversa.objects.exists())


    def test_paid_voice_note_charges_once_and_invalid_audio_is_free(self):
        import tempfile
        from uuid import uuid4
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from .test_conversations import historical_match
        from .test_voice_note_validation import wav_note
        from .chat_media_models import MensagemAudioMatchNKATA
        match = historical_match(perfil_1=self.a.perfil_nkata, perfil_2=self.b.perfil_nkata)
        self.move()
        self.client.force_login(self.a)
        url = f"/api/minha-conta/matches/{match.pk}/audio/"
        key = str(uuid4())
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory, NKATA_CREDIT_SPENDING_ENABLED=True):
            def send(audio, cost="2"):
                return self.client.post(url, {"audio": audio, "duracao_segundos": "2", "key": key, "expected_cost": cost})
            self.assertEqual(send(SimpleUploadedFile("fake.wav", b"invalid", content_type="audio/wav")).status_code, 400)
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 50)
            self.assertEqual(send(wav_note(2), "1").status_code, 409)
            first = send(wav_note(2))
            self.assertEqual(first.status_code, 201, first.content)
            retry = send(wav_note(2))
            self.assertEqual(retry.status_code, 200, retry.content)
            self.assertEqual(first.json()["id"], retry.json()["id"])
            self.assertEqual(wallet_snapshot(self.a)["saldo"], 48)
            self.assertEqual(MensagemAudioMatchNKATA.objects.filter(match=match).count(), 1)


    def test_inconsistent_wallet_rejects_new_debits_and_credits(self):
        self.move()
        CarteiraNKATA.objects.filter(usuario=self.a).update(saldo=100)
        for key, amount, kind in (("signal:1", -2, "CONSUMO"), ("pay:2", 50, "RECARGA")):
            with self.assertRaises(WalletError):
                self.move(key, amount, kind)
        self.assertEqual(CarteiraNKATA.objects.get(usuario=self.a).saldo, 100)
        self.assertEqual(MovimentoCreditoNKATA.objects.count(), 1)


    def test_personal_statement_filters_totals_and_privacy(self):
        from datetime import timedelta
        from django.utils import timezone
        self.move()
        self.move("signal:1", -2, "CONSUMO")
        self.move("chat24:1", -10, "CONSUMO")
        bonus = self.move("bonus:1", 5, "BONUS")
        MovimentoCreditoNKATA.objects.filter(pk=bonus.pk).update(criado_em=timezone.now()-timedelta(days=40))
        record_movement(self.b, key="secret", kind="RECARGA", amount=500, reference="private", reason="Outro membro")
        self.client.force_login(self.a)
        url = "/api/minha-conta/carteira/movimentos/"
        response = self.client.get(url, {"period":"30","kind":"CONSUMO","usuario":self.b.pk})
        self.assertEqual(response.status_code,200)
        self.assertIn("no-store", response["Cache-Control"])
        data=response.json()
        self.assertEqual(data["balance"],43)
        self.assertEqual(data["summary"]["spent"],12)
        self.assertEqual(data["summary"]["recharged"],50)
        self.assertEqual(data["summary"]["bonus"],0)
        self.assertEqual(len(data["results"]),2)
        self.assertEqual({r["code"]:r["credits"] for r in data["breakdown"]}["signals"],2)
        self.assertNotIn("Outro membro",str(data))
        self.assertEqual(self.client.get(url, {"period":"ALL"}).json()["summary"]["bonus"],5)
        self.assertEqual(self.client.get(url, {"period":"invalid"}).status_code,400)
        self.assertEqual(self.client.get(url, {"before":"-1"}).status_code,400)
        self.assertEqual(self.client.post(url, {"saldo":999}).status_code,405)

    def test_personal_statement_cursor_paginates_without_duplicates(self):
        for i in range(25):
            self.move(f"pay:{i}", 1)
        self.client.force_login(self.a)
        url="/api/minha-conta/carteira/movimentos/"
        first=self.client.get(url, {"period":"ALL"}).json()
        self.assertEqual(len(first["results"]),20)
        second=self.client.get(url, {"period":"ALL","before":first["next_before"]}).json()
        self.assertEqual(len(second["results"]),5)
        self.assertIsNone(second["next_before"])
        self.assertEqual(len({r["id"] for r in first["results"]+second["results"]}),25)
        self.assertEqual(second["balance"],25)


    def test_pdf_statement_uses_own_complete_filtered_ledger(self):
        from unittest.mock import patch
        for i in range(25):
            self.move(f"pdf:{i}",1)
        self.move("signal:pdf",-2,"CONSUMO")
        record_movement(self.b,key="other",kind="BONUS",amount=500,reference="private",reason="OUTRO_MEMBRO")
        self.client.force_login(self.a)
        url="/api/minha-conta/carteira/extrato.pdf"
        with patch("entradas.wallet_api.render_statement_pdf",return_value=b"%PDF-example") as render:
            response=self.client.get(url,{"period":"ALL","kind":"RECARGA","usuario":self.b.pk})
            self.assertEqual(response.status_code,200)
            data=render.call_args.args[0]
            self.assertEqual(len(data["results"]),25)
            self.assertEqual(data["balance"],23)
            self.assertEqual(data["summary"]["spent"],2)
            self.assertTrue(all(r["tipo"]=="RECARGA" for r in data["results"]))
            self.assertEqual(render.call_args.kwargs["member_id"],self.a.pk)
        response=self.client.get(url,{"period":"ALL"})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertEqual(response["Content-Type"],"application/pdf")
        self.assertIn("attachment",response["Content-Disposition"])
        self.assertIn("no-store",response["Cache-Control"])
        self.assertEqual(self.client.get(url,{"period":"invalid"}).status_code,400)
        self.client.logout()
        self.assertIn(self.client.get(url).status_code,(401,403))

    def test_pdf_statement_refuses_truncation(self):
        from unittest.mock import patch
        self.move()
        self.move("pdf:2",1)
        self.client.force_login(self.a)
        with patch("entradas.wallet_statement.EXPORT_LIMIT",1):
            response=self.client.get("/api/minha-conta/carteira/extrato.pdf",{"period":"ALL"})
        self.assertEqual(response.status_code,413)


    def test_statement_distinguishes_simulated_credits_from_purchases(self):
        self.move("real:1",100)
        self.move("simulated:1",50)
        self.client.force_login(self.a)
        data=self.client.get("/api/minha-conta/carteira/movimentos/",{"period":"ALL"}).json()
        self.assertEqual(data["balance"],150)
        self.assertEqual(data["summary"]["recharged"],100)
        self.assertEqual(data["summary"]["simulated_recharged"],50)
        self.assertEqual(data["summary"]["received"],150)


    def test_credit_only_chat_api_lifecycle_and_expiration(self):
        from uuid import uuid4
        from datetime import timedelta
        from django.utils import timezone
        from .models import Conversa, AcessoChatCreditoNKATA, MensagemMatch
        from .plan_service import CHAT_PHRASES_PT
        c = profile(92)
        first = Conversa.objects.create(perfil_1=self.a.perfil_nkata, perfil_2=self.b.perfil_nkata)
        second = Conversa.objects.create(perfil_1=self.a.perfil_nkata, perfil_2=c)
        self.move(amount=15)
        self.client.force_login(self.a)
        root = f"/api/chats/{first.pk}/"
        other = f"/api/chats/{second.pk}/"
        key = str(uuid4())
        with self.settings(NKATA_CREDIT_ONLY_ENABLED=True, NKATA_CREDIT_TRANSITION_ENABLED=True, NKATA_CREDIT_SPENDING_ENABLED=True):
            self.assertEqual(self.client.post(root, {"texto":"Mensagem livre de teste"}).status_code,403)
            self.assertEqual(self.client.post(root, {"texto":CHAT_PHRASES_PT[0]}).status_code,201)
            self.assertEqual(self.client.post(root+"quebra-gelo/", {"codigo":"VALORES"}).status_code,201)
            self.assertEqual(wallet_snapshot(self.a)["saldo"],15)
            self.assertEqual(self.client.post(root+"desbloquear/", {"key":key,"expected_cost":1},content_type="application/json").status_code,409)
            result=self.client.post(root+"desbloquear/", {"key":key,"expected_cost":10},content_type="application/json")
            self.assertEqual(result.status_code,200,result.content)
            self.assertTrue(result.json()["charged"])
            self.assertEqual(wallet_snapshot(self.a)["saldo"],5)
            for url, retry_key in ((root,key),(other,str(uuid4()))):
                repeat=self.client.post(url+"desbloquear/",{"key":retry_key,"expected_cost":10},content_type="application/json")
                self.assertEqual(repeat.status_code,200,repeat.content)
                self.assertFalse(repeat.json()["charged"])
                self.assertTrue(self.client.get(url).json()["texto_livre"])
                self.assertEqual(self.client.post(url,{"texto":"Mensagem livre de teste"}).status_code,201)
            self.client.force_login(self.b)
            self.assertFalse(self.client.get(root).json()["texto_livre"])
            self.assertEqual(self.client.post(root,{"texto":"Texto sem acesso"}).status_code,403)
            self.assertEqual(self.client.post(other+"desbloquear/",{"key":str(uuid4()),"expected_cost":10},content_type="application/json").status_code,404)
            self.client.force_login(self.a)
            now=timezone.now()
            AcessoChatCreditoNKATA.objects.filter(movimento__carteira__usuario=self.a).update(inicio=now-timedelta(days=1),fim=now)
            self.assertFalse(self.client.get(root).json()["texto_livre"])
            self.assertEqual(self.client.post(root,{"texto":"Texto depois da expiração"}).status_code,403)
            self.assertEqual(self.client.post(root,{"texto":CHAT_PHRASES_PT[1]}).status_code,201)
            retry=self.client.post(root+"desbloquear/",{"key":key,"expected_cost":10},content_type="application/json")
            self.assertEqual(retry.status_code,200)
            self.assertFalse(retry.json()["texto_livre"])
            self.assertFalse(retry.json()["charged"])
            self.assertEqual(self.client.post(root+"desbloquear/",{"key":str(uuid4()),"expected_cost":10},content_type="application/json").status_code,409)
            self.assertEqual(wallet_snapshot(self.a)["saldo"],5)
            self.assertEqual(MovimentoCreditoNKATA.objects.filter(carteira__usuario=self.a,tipo="CONSUMO").count(),1)
            self.assertFalse(MensagemMatch.objects.filter(texto="Texto depois da expiração").exists())

    def test_credit_only_signals_exact_costs_and_no_free_fallback(self):
        from .models import AcaoPerfil, Conversa
        chat=Conversa.objects.create(perfil_1=self.a.perfil_nkata,perfil_2=self.b.perfil_nkata)
        self.move(amount=6)
        self.client.force_login(self.a)
        url=f"/api/chats/{chat.pk}/sinais/"
        with self.settings(NKATA_CREDIT_ONLY_ENABLED=True,NKATA_CREDIT_TRANSITION_ENABLED=True,NKATA_CREDIT_SPENDING_ENABLED=True):
            for code,cost,balance in (("OLA",1,5),("FLOR",2,3),("BEIJINHO",3,0)):
                response=self.client.post(url,{"tipo":code,"expected_cost":cost},content_type="application/json")
                self.assertEqual(response.status_code,201,response.content)
                self.assertEqual(wallet_snapshot(self.a)["saldo"],balance)
            self.assertEqual(AcaoPerfil.objects.filter(usuario=self.a,tipo__startswith="SINAL_").count(),3)
            self.assertEqual(MovimentoCreditoNKATA.objects.filter(carteira__usuario=self.a,tipo="CONSUMO").count(),3)
            another=profile(93)
            profile_url=f"/api/perfis/{another.pk}/sinais/"
            self.assertEqual(self.client.post(profile_url,{"tipo":"OLA","expected_cost":1},content_type="application/json").status_code,429)
            with self.settings(NKATA_CREDIT_SPENDING_ENABLED=False):
                self.assertEqual(self.client.post(profile_url,{"tipo":"OLA","expected_cost":0},content_type="application/json").status_code,429)
            self.assertEqual(wallet_snapshot(self.a)["saldo"],0)

    def test_voice_insufficient_balance_and_storage_failure_do_not_charge(self):
        import tempfile
        from uuid import uuid4
        from unittest.mock import patch
        from django.test import override_settings
        from django.db import DatabaseError
        from .test_conversations import historical_match
        from .test_voice_note_validation import wav_note
        from .chat_media_models import MensagemAudioMatchNKATA
        match=historical_match(perfil_1=self.a.perfil_nkata,perfil_2=self.b.perfil_nkata)
        self.move(amount=1)
        self.client.force_login(self.a)
        url=f"/api/minha-conta/matches/{match.pk}/audio/"
        def send():
            return self.client.post(url,{"audio":wav_note(2),"duracao_segundos":"2","key":str(uuid4()),"expected_cost":"2"})
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory,NKATA_CREDIT_ONLY_ENABLED=True,NKATA_CREDIT_TRANSITION_ENABLED=True,NKATA_CREDIT_SPENDING_ENABLED=True):
            self.assertEqual(send().status_code,409)
            self.assertEqual(wallet_snapshot(self.a)["saldo"],1)
            self.move("fund:2",2)
            with patch("entradas.chat_media_api.MensagemAudioMatchNKATA.objects.create",side_effect=DatabaseError("simulated storage failure")):
                self.assertEqual(send().status_code,503)
            self.assertEqual(wallet_snapshot(self.a)["saldo"],3)
            self.assertFalse(MensagemAudioMatchNKATA.objects.filter(match=match).exists())
            self.assertEqual(MovimentoCreditoNKATA.objects.filter(carteira__usuario=self.a,tipo="CONSUMO").count(),0)
            self.assertEqual(send().status_code,201)
            self.assertEqual(wallet_snapshot(self.a)["saldo"],1)
