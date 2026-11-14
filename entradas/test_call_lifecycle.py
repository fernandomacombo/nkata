from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .call_api import _heartbeat_key
from .call_models import ChamadaMatchNKATA, SinalChamadaNKATA
from .models import PedidoEntrada, PerfilNKATA, MatchPerfil, QuestionarioEntrada
from .plan_service import assign_plan


class CallLifecycleTests(TestCase):
    @classmethod
    def setUpClass(cls):
        tables = set(connection.introspection.table_names())
        cls.created = [model for model in (ChamadaMatchNKATA, SinalChamadaNKATA)
                       if model._meta.db_table not in tables]
        call_command("setup_nkata_calls", verbosity=0)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as editor:
            for model in reversed(cls.created):
                editor.delete_model(model)

    def setUp(self):
        cache.clear()
        profiles = []
        self.users = []
        for index in range(2):
            email = f"call{index}@example.test"
            user = get_user_model().objects.create_user(username=email, email=email, password="Test-call-password")
            pedido = PedidoEntrada.objects.create(nome_completo="Test", email=email,
                telefone=f"84000000{index}", idade=30, cidade="Maputo", genero="MASCULINO",
                objetivo="RELACIONAMENTO_SERIO", status="APROVADO")
            QuestionarioEntrada.objects.create(pedido=pedido, disponibilidade="SIM", tem_filhos="NAO",
                aceita_pessoa_com_filhos="SIM", cidade_preferida="Maputo", faixa_etaria_preferida="25-40",
                sobre_si="Test", o_que_valoriza="Test", o_que_nao_aceita="Test", aceita_regras=True)
            profiles.append(PerfilNKATA.objects.create(pedido=pedido, usuario=user,
                nome_publico="Test", idade=30, status="ATIVO"))
            assign_plan(user, "ESSENCIAL")
            self.users.append(user)
        self.match = MatchPerfil.objects.create(perfil_1=profiles[0], perfil_2=profiles[1])
        self.client = APIClient()
        self.url = f"/api/minha-conta/matches/{self.match.pk}/call/"

    def post(self, user, **data):
        self.client.force_authenticate(user)
        return self.client.post(self.url, data, format="json")

    def start(self):
        response = self.post(self.users[0], action="start", type="AUDIO")
        self.assertEqual(response.status_code, 201, response.data)
        return ChamadaMatchNKATA.objects.get(pk=response.data["call"]["id"])

    def test_caller_cannot_mark_unaccepted_call_active(self):
        call = self.start()
        response = self.post(self.users[0], action="active", call_id=call.pk)
        self.assertEqual(response.status_code, 409)
        call.refresh_from_db()
        self.assertEqual(call.estado, "CHAMANDO")

    def test_abandoned_negotiation_recovers_for_next_call(self):
        call = self.start()
        self.assertEqual(self.post(self.users[1], action="accept", call_id=call.pk).status_code, 200)
        ChamadaMatchNKATA.objects.filter(pk=call.pk).update(atualizada_em=timezone.now()-timedelta(minutes=2))
        self.client.get(self.url)
        call.refresh_from_db()
        self.assertEqual(call.estado, "FALHOU")
        self.start()

    def test_missing_remote_heartbeat_ends_active_call(self):
        call = self.start()
        self.post(self.users[1], action="accept", call_id=call.pk)
        self.post(self.users[0], action="active", call_id=call.pk)
        cache.set(_heartbeat_key(call, self.users[1].pk), (timezone.now()-timedelta(minutes=2)).timestamp())
        self.client.force_authenticate(self.users[0])
        response = self.client.get(self.url)
        self.assertIsNone(response.data["call"])
        call.refresh_from_db()
        self.assertEqual(call.estado, "FALHOU")
        self.start()

    def test_live_heartbeats_preserve_call_and_end_releases_it(self):
        call = self.start()
        self.post(self.users[1], action="accept", call_id=call.pk)
        self.post(self.users[0], action="active", call_id=call.pk)
        for user in self.users:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.url).data["call"]["estado"], "ATIVA")
        self.assertEqual(self.post(self.users[1], action="end", call_id=call.pk).status_code, 200)
        self.start()
