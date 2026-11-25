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
        for peer in (self.a, self.b):
            token=self.issue(peer.usuario).json()["ticket"]
            self.assertEqual(self.redeem(token).status_code,200)
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

    def issue(self, user):
        self.client.force_login(user)
        return self.client.post(f"/api/chats/chamadas/{self.call.pk}/ticket/", secure=True)

    def redeem(self, ticket, secret=SECRET):
        from .media_gateway_api import JOIN_PATH
        body=json.dumps({"ticket":ticket})
        stamp=str(int(time.time()))
        nonce=str(uuid4())
        signature=hmac.new(secret.encode(),f"POST\n{JOIN_PATH}\n{stamp}\n{nonce}\n".encode()+body.encode(),hashlib.sha256).hexdigest()
        return self.client.post(JOIN_PATH,body,content_type="application/json",secure=True,
            HTTP_X_NKATA_MEDIA_TIME=stamp,HTTP_X_NKATA_MEDIA_NONCE=nonce,HTTP_X_NKATA_MEDIA_SIGNATURE=signature)

    def test_join_only_authorized_participants_once_without_charge(self):
        other=profile(82)
        self.assertEqual(self.issue(other.usuario).status_code,404)
        first=self.issue(self.a.usuario)
        self.assertEqual(first.status_code,200,first.content)
        token=first.json()["ticket"]
        self.assertEqual(self.redeem(token,secret="wrong").status_code,403)
        accepted=self.redeem(token)
        self.assertEqual(accepted.status_code,200,accepted.content)
        self.assertEqual(accepted.json()["user_id"],self.a.usuario_id)
        self.assertEqual(self.redeem(token).status_code,409)
        second=self.issue(self.a.usuario).json()["ticket"]
        self.assertEqual(self.redeem(second).status_code,409)
        peer=self.issue(self.b.usuario).json()["ticket"]
        self.assertEqual(self.redeem(peer).json()["user_id"],self.b.usuario_id)
        self.assertEqual(credit_balance(self.a.usuario),9)

    def test_join_revoked_or_disabled_never_charges(self):
        from .native_call_service import end_call
        token=self.issue(self.a.usuario).json()["ticket"]
        with self.settings(NKATA_MEDIA_GATEWAY_TEST_ENABLED=False):
            self.assertEqual(self.redeem(token).status_code,404)
        end_call(self.call.pk,actor_id=self.b.usuario_id)
        self.assertEqual(self.redeem(token).status_code,403)
        self.assertEqual(credit_balance(self.a.usuario),9)

    def test_both_participants_must_be_admitted_before_billing(self):
        self.assertEqual(self.signed().status_code,409)
        token=self.issue(self.a.usuario).json()["ticket"]
        self.assertEqual(self.redeem(token).status_code,200)
        self.assertEqual(self.signed().status_code,409)
        self.assertEqual(credit_balance(self.a.usuario),9)
        token=self.issue(self.b.usuario).json()["ticket"]
        self.assertEqual(self.redeem(token).status_code,200)
        self.assertEqual(self.signed().status_code,200)
        self.assertEqual(credit_balance(self.a.usuario),6)


    def ice(self, user):
        self.client.force_login(user)
        return self.client.post(f"/api/chats/chamadas/{self.call.pk}/ice/", secure=True)

    @override_settings(NKATA_WEBRTC_TURN_URLS=["turn:relay.example.test:3478?transport=udp",
        "turns:relay.example.test:5349?transport=tcp"],
        NKATA_WEBRTC_TURN_SHARED_SECRET="relay-only-"+"x"*40)
    def test_ice_credentials_require_participation_and_expire(self):
        import base64
        outsider=profile(82)
        self.assertEqual(self.ice(outsider.usuario).status_code,404)
        with patch("entradas.webrtc_credentials.time.time",return_value=1000000):
            response=self.ice(self.a.usuario)
        self.assertEqual(response.status_code,200,response.content)
        self.assertEqual(response["Cache-Control"],"no-store")
        result=response.json()
        turn=result["ice_servers"][-1]
        expected_expiry=1000000+3*60+300
        self.assertEqual(result["expires_at"],expected_expiry)
        self.assertEqual(turn["username"],f"{expected_expiry}:{self.call.pk}:{self.a.usuario_id}")
        expected=base64.b64encode(hmac.new(("relay-only-"+"x"*40).encode(),
                            turn["username"].encode(),hashlib.sha1).digest()).decode()
        self.assertEqual(turn["credential"],expected)
        self.assertNotIn("relay-only-",response.content.decode())
        self.assertEqual(credit_balance(self.a.usuario),9)

    @override_settings(NKATA_WEBRTC_TURN_URLS=["turns:relay.example.test:5349?transport=tcp"],
        NKATA_WEBRTC_TURN_SHARED_SECRET="",NKATA_WEBRTC_TURN_USERNAME="fixed",
        NKATA_WEBRTC_TURN_CREDENTIAL="fixed-password")
    def test_native_ice_never_falls_back_to_static_credentials(self):
        self.assertEqual(self.ice(self.a.usuario).status_code,503)
        with self.settings(NKATA_MEDIA_GATEWAY_TEST_ENABLED=False):
            self.assertEqual(self.ice(self.a.usuario).status_code,404)

    @override_settings(NKATA_WEBRTC_TURN_URLS=["turns:relay.example.test:5349?transport=tcp"],
        NKATA_WEBRTC_TURN_SHARED_SECRET="relay-only-"+"x"*40)
    def test_ice_denied_after_call_ends(self):
        from .native_call_service import end_call
        end_call(self.call.pk,actor_id=self.b.usuario_id)
        self.assertEqual(self.ice(self.a.usuario).status_code,404)


    def test_native_call_browser_lifecycle_without_debit(self):
        from .native_call_service import end_call
        end_call(self.call.pk, actor_id=self.a.usuario_id)
        self.client.force_login(self.a.usuario)
        url=f"/api/chats/{self.call.conversa_id}/chamadas/"
        body={"key":str(uuid4()),"kind":"AUDIO","expected_rate":3,"max_minutes":3}
        response=self.client.post(url,json.dumps(body),content_type="application/json",secure=True)
        self.assertEqual(response.status_code,201,response.content)
        sid=response.json()["id"]
        self.assertEqual(response.json()["state"],"CHAMANDO")
        self.assertEqual(self.client.post(url,json.dumps(body),content_type="application/json",secure=True).json()["id"],sid)
        detail=f"/api/chats/chamadas/{sid}/"
        self.assertEqual(self.client.post(detail,{"action":"accept"},secure=True).status_code,404)
        self.client.force_login(self.b.usuario)
        incoming=self.client.get("/api/chats/chamadas/actual/",secure=True).json()["call"]
        self.assertEqual(incoming["id"],sid)
        self.assertIsNone(incoming["balance"])
        self.assertEqual(self.client.post(detail,{"action":"accept"},secure=True).json()["state"],"ACEITE")
        self.assertEqual(self.client.post(detail,{"action":"end"},secure=True).json()["state"],"TERMINADA")
        self.assertIsNone(self.client.get("/api/chats/chamadas/actual/",secure=True).json()["call"])
        self.assertEqual(credit_balance(self.a.usuario),9)

    def test_browser_call_api_rejects_outsider_and_production(self):
        outsider=profile(82)
        self.client.force_login(outsider.usuario)
        detail=f"/api/chats/chamadas/{self.call.pk}/"
        self.assertEqual(self.client.get(detail,secure=True).status_code,404)
        self.assertEqual(self.client.post(detail,{"action":"end"},secure=True).status_code,404)
        self.client.force_login(self.a.usuario)
        with self.settings(NKATA_MEDIA_GATEWAY_TEST_ENABLED=False):
            self.assertEqual(self.client.get(detail,secure=True).status_code,404)
        self.assertEqual(credit_balance(self.a.usuario),9)


    def reconcile(self, minute=1, secret=SECRET, ids=None, outcome="RESUME_NOT_ATTEMPTED"):
        from .media_gateway_api import RECONCILE_PATH
        body=json.dumps({"session_id":str(self.call.pk),
            "user_ids":ids or [self.a.usuario_id,self.b.usuario_id],"minute":minute,"outcome":outcome})
        stamp=str(int(time.time()))
        nonce=str(uuid4())
        signature=hmac.new(secret.encode(),f"POST\n{RECONCILE_PATH}\n{stamp}\n{nonce}\n".encode()+body.encode(),hashlib.sha256).hexdigest()
        return self.client.post(RECONCILE_PATH,body,content_type="application/json",secure=True,
            HTTP_X_NKATA_MEDIA_TIME=stamp,HTTP_X_NKATA_MEDIA_NONCE=nonce,HTTP_X_NKATA_MEDIA_SIGNATURE=signature)

    def test_reconciliation_refunds_only_once_and_preserves_original_debit(self):
        from .models import MovimentoCreditoNKATA
        for peer in (self.a,self.b):
            self.assertEqual(self.redeem(self.issue(peer.usuario).json()["ticket"]).status_code,200)
        self.assertEqual(self.signed().status_code,200)
        self.assertEqual(credit_balance(self.a.usuario),6)
        self.assertEqual(self.reconcile(secret="wrong").status_code,403)
        self.assertEqual(self.reconcile(outcome="UNKNOWN").status_code,400)
        self.assertEqual(self.reconcile(ids=[self.a.usuario_id,999999]).status_code,409)
        self.assertEqual(self.reconcile().json()["refunded"],3)
        self.assertEqual(self.reconcile().json()["refunded"],3)
        self.assertEqual(credit_balance(self.a.usuario),9)
        key=f"call:native:{self.call.pk}:minute:1"
        self.assertEqual(MovimentoCreditoNKATA.objects.get(chave=key).quantidade,-3)
        self.assertEqual(MovimentoCreditoNKATA.objects.get(chave=key+":refund").quantidade,3)
        self.assertEqual(self.signed(index=2).status_code,409)
        self.call.refresh_from_db()
        self.assertEqual(self.call.estado,"TERMINADA")

    def test_reconciliation_before_debit_closes_session_without_creating_credit(self):
        for peer in (self.a,self.b):
            self.assertEqual(self.redeem(self.issue(peer.usuario).json()["ticket"]).status_code,200)
        self.assertEqual(self.reconcile().json()["refunded"],0)
        self.assertEqual(self.signed().status_code,409)
        self.assertEqual(credit_balance(self.a.usuario),9)


    def test_durable_resume_intent_prevents_automatic_refund(self):
        from .models import RevisaoMinutoChamadaNKATA
        from .native_call_service import mark_gateway_resume
        for peer in (self.a,self.b):
            self.assertEqual(self.redeem(self.issue(peer.usuario).json()["ticket"]).status_code,200)
        self.assertEqual(self.signed().status_code,200)
        row=RevisaoMinutoChamadaNKATA.objects.get(chamada=self.call,minuto=1)
        self.assertEqual(row.estado,"AUTORIZADO")
        ids=[self.a.usuario_id,self.b.usuario_id]
        self.assertEqual(mark_gateway_resume(self.call.pk,user_ids=ids,minute=1,phase="INTENT"),"RETOMA_INICIADA")
        self.assertEqual(self.reconcile().status_code,409)
        self.assertEqual(credit_balance(self.a.usuario),6)
        self.assertEqual(mark_gateway_resume(self.call.pk,user_ids=ids,minute=1,phase="CONFIRMED"),"CONFIRMADO")
        row.refresh_from_db()
        self.assertEqual(row.estado,"CONFIRMADO")


    def test_browser_config_requires_explicit_staging_and_turn(self):
        url="/api/chats/chamadas/config/"
        self.client.force_login(self.a.usuario)
        self.assertFalse(self.client.get(url,secure=True).json()["enabled"])
        with self.settings(NKATA_MEDIA_BROWSER_TEST_ENABLED=True,
                NKATA_MEDIA_STAGING_SIGNAL_URL="wss://media-staging.example.test/signal",
                NKATA_WEBRTC_TURN_SHARED_SECRET="t"*40,
                NKATA_WEBRTC_TURN_URLS=["turns:relay.example.test"]):
            with patch("entradas.native_call_api.welcome_eligible",return_value=True):
                self.assertEqual(self.client.get(url,secure=True).json(),
                    {"enabled":True,"signal_url":"wss://media-staging.example.test/signal"})
            with patch("entradas.native_call_api.welcome_eligible",return_value=False):
                self.assertFalse(self.client.get(url,secure=True).json()["enabled"])
            with self.settings(NKATA_RAILWAY_ENVIRONMENT_ID="production"):
                self.assertEqual(self.client.get(url,secure=True).status_code,404)
            with self.settings(NKATA_MEDIA_STAGING_SIGNAL_URL="wss://nkata.date/signal"):
                with patch("entradas.native_call_api.welcome_eligible",return_value=True):
                    self.assertFalse(self.client.get(url,secure=True).json()["enabled"])
