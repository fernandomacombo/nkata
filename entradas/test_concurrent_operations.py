from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch
import uuid

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from .account_limits import save_limited_request
from .models import PedidoEntrada, PerfilNKATA, MatchPerfil, AcessoPlanoNKATA, PedidoPagamentoNKATA, QuestionarioEntrada
from .plan_service import assign_plan
from .payment_service import reconcile
from .test_account_limits import request_form
from .test_call_lifecycle import CallLifecycleTests


@skipUnless(connection.vendor == "postgresql", "Row-lock concurrency requires PostgreSQL")
class ConcurrentOperationsTests(TransactionTestCase):
    available_apps = [config.name for config in apps.get_app_configs()]

    def race(self, function):
        barrier = Barrier(2)

        def run(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return function(index)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run, index) for index in range(2)]
            return [future.result(timeout=20) for future in futures]

    def test_only_one_concurrent_registration_can_claim_an_identity(self):
        def register(index):
            try:
                save_limited_request(request_form(f"racer{index}@example.test", f"85000000{index}", "110100000001A"))
                return 201
            except ValidationError:
                return 409

        self.assertEqual(sorted(self.race(register)), [201, 409])
        self.assertEqual(PedidoEntrada.objects.count(), 1)

    def test_shared_participant_cannot_start_two_matches_concurrently(self):
        CallLifecycleTests.setUp(self)
        third = get_user_model().objects.create_user(username="third", email="third@example.test", password="Test-call-password")
        pedido = PedidoEntrada.objects.create(nome_completo="Third", email=third.email,
            telefone="840000009", idade=30, status="APROVADO")
        QuestionarioEntrada.objects.create(pedido=pedido, disponibilidade="SIM", tem_filhos="NAO",
            aceita_pessoa_com_filhos="SIM", cidade_preferida="Maputo", faixa_etaria_preferida="25-40",
            sobre_si="Test", o_que_valoriza="Test", o_que_nao_aceita="Test", aceita_regras=True)
        profile = PerfilNKATA.objects.create(pedido=pedido, usuario=third, nome_publico="Third", idade=30)
        assign_plan(third, "ESSENCIAL")
        second = MatchPerfil.objects.create(perfil_1=self.users[0].perfil_nkata, perfil_2=profile)
        match_ids = [self.match.pk, second.pk]

        def start(index):
            client = APIClient()
            client.force_authenticate(self.users[0])
            return client.post(f"/api/minha-conta/matches/{match_ids[index]}/call/",
                {"action":"start", "type":"AUDIO"}, format="json").status_code

        self.assertEqual(sorted(self.race(start)), [201, 409])

    def test_concurrent_payment_confirmations_extend_plan_once(self):
        CallLifecycleTests.setUp(self)
        user = self.users[0]
        before = AcessoPlanoNKATA.objects.get(usuario=user).fim
        order = PedidoPagamentoNKATA.objects.create(usuario=user, chave=uuid.uuid4(), referencia="NKATATESTCONCURRENT",
            produto="ESSENCIAL", valor=250, dias=30, provedor_id="PAYTEST1", estado="PENDENTE")
        data = {"id":order.provedor_id, "reference":order.referencia, "amount":"250.00",
            "status":"completed", "transaction":{"status":"completed", "transaction_id":"TXTEST1"}}
        with patch("entradas.payment_service.provider_request", return_value=data):
            results = self.race(lambda index: reconcile(order).estado)
        self.assertEqual(results, ["PAGO", "PAGO"])
        self.assertEqual(AcessoPlanoNKATA.objects.get(usuario=user).fim, before + timedelta(days=30))
