import hashlib
import hmac
import json
import time
from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import Conversa
from .test_conversations import profile
from .native_call_service import prepare_call, decide_call
from .wallet_service import record_movement, credit_balance
from .media_gateway_api import PATH

SECRET="test-only-"+"x"*40
@override_settings(NKATA_MEDIA_GATEWAY_TEST_ENABLED=True,NKATA_MEDIA_GATEWAY_SECRET=SECRET,
    NKATA_RAILWAY_ENVIRONMENT_ID="36306a53-86bc-4a07-9b09-7c42c58f2e43",
    NKATA_PAYMENT_SIMULATION_ENABLED=True,NKATA_PAYMENTS_ENABLED=False,
    NKATA_CREDIT_ONLY_ENABLED=True,NKATA_CREDIT_TRANSITION_ENABLED=True,NKATA_CREDIT_SPENDING_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend")
class MediaGatewayTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a,self.b=profile(80),profile(81)
        chat=Conversa.objects.create(perfil_1=self.a,perfil_2=self.b)
        record_movement(self.a.usuario,key="fund",kind="RECARGA",amount=9,reference="fund",reason="Test")
        self.call=prepare_call(chat.pk,caller_id=self.a.usuario_id,key=uuid4(),kind="AUDIO",expected_rate=3,max_minutes=3)
        decide_call(self.call.pk,recipient_id=self.b.usuario_id,accept=True)

    def signed(self,index=1,nonce=None,stamp=None,secret=SECRET,ids=None):
        body=json.dumps({"session_id":str(self.call.pk),"connected_user_ids":ids or [self.a.usuario_id,self.b.usuario_id],"expected_minute":index})
        stamp=str(int(time.time()) if stamp is None else stamp)
        nonce=nonce or str(uuid4())
        signature=hmac.new(secret.encode(),f"POST\n{PATH}\n{stamp}\n{nonce}\n".encode()+body.encode(),hashlib.sha256).hexdigest()
        return self.client.post(PATH,body,content_type="application/json",secure=True,HTTP_X_NKATA_MEDIA_TIME=stamp,HTTP_X_NKATA_MEDIA_NONCE=nonce,HTTP_X_NKATA_MEDIA_SIGNATURE=signature)

    def test_requires_gateway_signature_and_isolated_staging(self):
        self.assertEqual(self.signed(secret="wrong").status_code,403)
        self.assertEqual(self.signed(stamp=int(time.time())-40).status_code,403)
        with self.settings(NKATA_RAILWAY_ENVIRONMENT_ID="production"):
            self.assertEqual(self.signed().status_code,404)
        with self.settings(NKATA_MEDIA_GATEWAY_TEST_ENABLED=False):
            self.assertEqual(self.signed().status_code,404)
        self.assertEqual(credit_balance(self.a.usuario),9)

    def test_replay_and_minute_index_cannot_charge_twice(self):
        nonce=str(uuid4())
        first=self.signed(nonce=nonce)
        self.assertEqual(first.status_code,200,first.content)
        self.assertEqual(self.signed(nonce=nonce).status_code,409)
        self.assertEqual(self.signed().json()["paid_until"],first.json()["paid_until"])
        self.assertEqual(self.signed(index=2).status_code,409)
        self.assertEqual(credit_balance(self.a.usuario),6)
        self.call.refresh_from_db()
        with patch("entradas.native_call_service.timezone.now",return_value=self.call.pago_ate):
            self.assertEqual(self.signed(index=1).status_code,409)
            self.assertEqual(self.signed(index=2).status_code,200)
        self.assertEqual(credit_balance(self.a.usuario),3)
