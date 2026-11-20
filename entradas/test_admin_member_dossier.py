from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import PedidoEntrada, PerfilNKATA, PedidoPagamentoNKATA
from .user_roles import set_admin_capabilities


class MemberDossierTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_dossier", email="owner@example.org", password="test-safe-password",
        )
        self.staff = User.objects.create_user(
            username="member_operator", email="operator@example.org",
            password="test-safe-password", is_staff=True,
        )
        self.other_staff = User.objects.create_user(
            username="no_members", email="other@example.org",
            password="test-safe-password", is_staff=True,
        )
        set_admin_capabilities(self.staff, ["members"])
        set_admin_capabilities(self.other_staff, ["overview"])
        self.request_record = PedidoEntrada.objects.create(
            nome_completo="Test Person",
            email="owner@example.org", telefone="840000888", idade=30,
            cidade="Maputo", genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
            foto_perfil="pedidos/fotos/testing.jpg", status="APROVADO",
            verificacao_apos_entrada=True, documento_confirmado=False,
        )
        self.profile = PerfilNKATA.objects.create(
            pedido=self.request_record, usuario=self.owner,
            nome_publico="Pessoa de Teste", cidade="Maputo", idade=30,
            genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Perfil de teste", o_que_valoriza="Respeito",
            o_que_nao_aceita="Mentiras", status="ATIVO", visivel=True,
        )
        self.url = reverse("entradas_api:admin_member_dossier", kwargs={"profile_id": self.profile.pk})

    def test_member_cannot_read_admin_dossier(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_operator_without_members_permission_is_denied(self):
        self.client.force_login(self.other_staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_authorized_operator_sees_summary_but_no_private_evidence(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["member"]["name"], "Pessoa de Teste")
        self.assertFalse(payload["identity"]["confirmed"])
        self.assertEqual(payload["identity"]["nkata_id_status"], "POR_INICIAR")
        self.assertEqual(payload["payments"]["total"], 0)
        self.assertEqual(payload["activity"]["matches"], 0)
        self.assertNotIn("bi_frente", str(payload))
        self.assertNotIn("selfie_ao_vivo", str(payload))
        self.assertNotIn("documento_chave", str(payload))
        self.assertNotIn("password", str(payload))
