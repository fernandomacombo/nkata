from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import Conversa, MovimentoCreditoNKATA, AcaoPerfil
from .test_conversations import profile, historical_match
from .wallet_service import record_movement, credit_balance, WalletError
from .native_call_service import prepare_call, decide_call, authorize_gateway_minute, end_call

@override_settings(NKATA_CREDIT_ONLY_ENABLED=True,NKATA_CREDIT_TRANSITION_ENABLED=True,NKATA_CREDIT_SPENDING_ENABLED=True)
class NativeCallTests(TestCase):
    def setUp(self):
        self.a,self.b,self.c=[profile(i) for i in (80,81,82)]
        self.chat=Conversa.objects.create(perfil_1=self.a,perfil_2=self.b)
        self.caller=self.a.usuario
        self.recipient=self.b.usuario
        self.ids=[self.caller.pk,self.recipient.pk]
        record_movement(self.caller,key="fund",kind="RECARGA",amount=11,reference="fund",reason="Test")

    def prepare(self,kind="AUDIO",rate=3,key=None):
        return prepare_call(self.chat.pk,caller_id=self.caller.pk,key=key or uuid4(),kind=kind,expected_rate=rate,max_minutes=5)

    def test_billing_only_after_acceptance_and_trusted_media(self):
        key=uuid4()
        call=self.prepare(key=key)
        self.assertEqual(self.prepare(key=key).pk,call.pk)
        self.assertIsNone(authorize_gateway_minute(call.pk,connected_user_ids=self.ids))
        self.assertEqual(credit_balance(self.caller),11)
        with self.assertRaises(WalletError):
            decide_call(call.pk,recipient_id=self.caller.pk,accept=True)
        decide_call(call.pk,recipient_id=self.recipient.pk,accept=True)
        first=authorize_gateway_minute(call.pk,connected_user_ids=self.ids)
        self.assertIsNotNone(first)
        self.assertEqual(authorize_gateway_minute(call.pk,connected_user_ids=self.ids),first)
        self.assertEqual(credit_balance(self.caller),8)
        self.assertEqual(credit_balance(self.recipient),0)
        with patch("entradas.native_call_service.timezone.now",return_value=first):
            second=authorize_gateway_minute(call.pk,connected_user_ids=self.ids)
        self.assertEqual(second,first+timedelta(seconds=60))
        self.assertEqual(credit_balance(self.caller),5)
        with patch("entradas.native_call_service.timezone.now",return_value=second+timedelta(seconds=6)):
            self.assertIsNone(authorize_gateway_minute(call.pk,connected_user_ids=self.ids))
        self.assertEqual(credit_balance(self.caller),5)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(tipo="CONSUMO").count(),2)

    def test_video_insufficient_balance_stops_before_new_minute(self):
        call=self.prepare("VIDEO",5)
        decide_call(call.pk,recipient_id=self.recipient.pk,accept=True)
        first=authorize_gateway_minute(call.pk,connected_user_ids=self.ids)
        with patch("entradas.native_call_service.timezone.now",return_value=first):
            second=authorize_gateway_minute(call.pk,connected_user_ids=self.ids)
        with patch("entradas.native_call_service.timezone.now",return_value=second):
            self.assertIsNone(authorize_gateway_minute(call.pk,connected_user_ids=self.ids))
        self.assertEqual(credit_balance(self.caller),1)

    def test_refusal_and_block_never_charge(self):
        call=self.prepare()
        decide_call(call.pk,recipient_id=self.recipient.pk,accept=False)
        self.assertIsNone(authorize_gateway_minute(call.pk,connected_user_ids=self.ids))
        call=self.prepare()
        decide_call(call.pk,recipient_id=self.recipient.pk,accept=True)
        AcaoPerfil.objects.create(usuario=self.recipient,perfil=self.a,tipo="BLOQUEIO")
        self.assertIsNone(authorize_gateway_minute(call.pk,connected_user_ids=self.ids))
        self.assertEqual(credit_balance(self.caller),11)

    def test_missing_peer_ends_session_without_charge(self):
        call=self.prepare()
        decide_call(call.pk,recipient_id=self.recipient.pk,accept=True)
        self.assertIsNone(authorize_gateway_minute(call.pk,connected_user_ids=[self.caller.pk]))
        self.assertEqual(credit_balance(self.caller),11)

    def test_participant_busy_and_end_releases(self):
        call=self.prepare()
        other=Conversa.objects.create(perfil_1=self.a,perfil_2=self.c)
        with self.assertRaises(WalletError):
            prepare_call(other.pk,caller_id=self.caller.pk,key=uuid4(),kind="AUDIO",expected_rate=3,max_minutes=1)
        with self.assertRaises(WalletError):
            end_call(call.pk,actor_id=self.c.usuario_id)
        end_call(call.pk,actor_id=self.recipient.pk)
        self.assertNotEqual(self.prepare().pk,call.pk)
