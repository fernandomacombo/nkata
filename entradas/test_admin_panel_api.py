from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .admin_panel_api import _admin_call_duration_seconds, _admin_call_status
from .call_models import ChamadaMatchNKATA
from .models import PedidoEntrada, PerfilNKATA, QuestionarioEntrada
from .posts_models import PublicacaoNKATA


def create_request(email, status="APROVADO"):
    return PedidoEntrada.objects.create(
        nome_completo="Membro de Teste",
        email=email,
        telefone="840000000",
        idade=31,
        cidade="Maputo",
        genero="FEMININO",
        objetivo="RELACIONAMENTO_SERIO",
        aceita_verificacao=True,
        foto_perfil="pedidos/fotos/perfil.jpg",
        foto_extra_1="pedidos/fotos/extra-1.jpg",
        foto_extra_2="pedidos/fotos/extra-2.jpg",
        foto_extra_3="pedidos/fotos/extra-3.jpg",
        bi_frente="pedidos/documentos/frente.jpg",
        bi_verso="pedidos/documentos/verso.jpg",
        selfie_com_bi="pedidos/documentos/selfie.jpg",
        status=status,
    )


class AdminPanelApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="operador",
            email="operador@nkata.test",
            password="senha-segura",
            is_staff=True,
        )
        self.member_user = User.objects.create_user(
            username="membro",
            email="membro@nkata.test",
            password="senha-segura",
        )
        self.request_record = create_request("membro@nkata.test")
        QuestionarioEntrada.objects.create(
            pedido=self.request_record,
            disponibilidade="SIM",
            tem_filhos="NAO",
            aceita_pessoa_com_filhos="SIM",
            cidade_preferida="Maputo",
            faixa_etaria_preferida="28 a 38 anos",
            sobre_si="Uma pessoa tranquila.",
            o_que_valoriza="Respeito.",
            o_que_nao_aceita="Desrespeito.",
            aceita_regras=True,
        )
        self.profile = PerfilNKATA.objects.create(
            pedido=self.request_record,
            usuario=self.member_user,
            nome_publico="Membro",
            cidade="Maputo",
            idade=31,
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Uma pessoa tranquila.",
            o_que_valoriza="Respeito.",
            o_que_nao_aceita="Desrespeito.",
            status="ATIVO",
            visivel=True,
        )

    def test_regular_member_cannot_access_panel(self):
        self.client.force_authenticate(self.member_user)
        response = self.client.get(reverse("entradas_api:admin_summary"))
        self.assertEqual(response.status_code, 403)

    def test_staff_session_exposes_admin_capability(self):
        self.client.force_authenticate(self.staff)
        response = self.client.get(reverse("entradas_api:session"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["user"]["is_staff"])
        self.assertFalse(response.data["user"]["is_superuser"])

    def test_staff_can_read_summary_and_members(self):
        self.client.force_authenticate(self.staff)
        summary = self.client.get(reverse("entradas_api:admin_summary"))
        members = self.client.get(
            reverse("entradas_api:admin_list"),
            {"section": "members"},
        )
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["metrics"]["members_total"], 1)
        self.assertEqual(members.status_code, 200)
        self.assertEqual(members.data["total"], 1)
        self.assertEqual(members.data["results"][0]["name"], "Membro")

    def test_staff_can_pause_member(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {"resource": "member", "action": "pause", "id": self.profile.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, "PAUSADO")
        self.assertFalse(self.profile.visivel)

    def test_staff_can_approve_access_request(self):
        pending = create_request("candidato@nkata.test", status="PENDENTE")
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {"resource": "access", "action": "approve", "id": pending.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, "APROVADO")

    def test_staff_can_approve_pending_content(self):
        publication = PublicacaoNKATA.objects.create(
            perfil=self.profile,
            usuario=self.member_user,
            media="posts/2026/08/09/publicacao.jpg",
            tipo_media="IMAGEM",
            legenda="Um bom momento.",
            visibilidade="TODOS",
            moderacao_status="PENDENTE",
        )
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {
                "resource": "content",
                "content_type": "PUBLICACAO",
                "action": "approve",
                "id": publication.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        publication.refresh_from_db()
        self.assertEqual(publication.moderacao_status, "APROVADO")
        self.assertIsNotNone(publication.moderado_em)


class AdminCallPresentationTests(SimpleTestCase):
    def test_connected_call_shows_only_real_connected_duration(self):
        ended_at = timezone.now()
        call = SimpleNamespace(
            estado=ChamadaMatchNKATA.ESTADO_TERMINADA,
            atendida_em=ended_at - timedelta(seconds=18),
            terminada_em=ended_at,
            get_estado_display=lambda: "Terminada",
        )

        self.assertEqual(_admin_call_duration_seconds(call), 18)
        self.assertEqual(_admin_call_status(call), ("TERMINADA", "Terminada"))

    def test_ended_call_without_connection_is_not_presented_as_completed(self):
        call = SimpleNamespace(
            estado=ChamadaMatchNKATA.ESTADO_TERMINADA,
            atendida_em=None,
            terminada_em=timezone.now(),
            get_estado_display=lambda: "Terminada",
        )

        self.assertEqual(_admin_call_duration_seconds(call), 0)
        self.assertEqual(
            _admin_call_status(call),
            ("SEM_ATENDIMENTO", "Sem atendimento"),
        )
