from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import PedidoEntrada, PerfilNKATA
from .moments_models import MomentoNKATA
from .plan_service import plan_code_for_user
from .user_roles import set_admin_capabilities


def create_member(email="membro@nkata.test"):
    user = User.objects.create_user(username=email, email=email, password="senha-segura")
    request_record = PedidoEntrada.objects.create(
        nome_completo="Membro Teste", email=email, telefone="840001111", idade=32,
        cidade="Maputo", genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
        aceita_verificacao=True, status="APROVADO",
    )
    profile = PerfilNKATA.objects.create(
        pedido=request_record, usuario=user, nome_publico="Membro", cidade="Maputo",
        idade=32, genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
        sobre_si="Apresentação completa de uma pessoa tranquila.",
        o_que_valoriza="Respeito e honestidade.", o_que_nao_aceita="Desrespeito.",
        status="ATIVO", visivel=True,
    )
    PerfilNKATA.objects.filter(pk=profile.pk).update(status="ATIVO", visivel=True)
    profile.refresh_from_db()
    return user, profile


class GovernanceRulesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member, self.profile = create_member()
        self.staff = User.objects.create_user(
            username="staff@nkata.test", email="staff@nkata.test",
            password="senha-staff-segura", is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="root@nkata.test", email="root@nkata.test", password="senha-root-segura",
        )

    def test_operator_never_receives_normal_member_profile(self):
        self.profile.usuario = self.staff
        self.profile.save(update_fields=["usuario"])
        self.client.force_authenticate(self.staff)
        session = self.client.get(reverse("entradas_api:session"))
        profiles = self.client.get(reverse("entradas_api:perfis"))
        self.assertIsNone(session.data["profile"])
        self.assertEqual(profiles.status_code, 403)

    def test_staff_only_accesses_capabilities_granted_by_superuser(self):
        set_admin_capabilities(self.staff, ["access"])
        self.client.force_authenticate(self.staff)
        access = self.client.get(reverse("entradas_api:admin_list"), {"section": "access"})
        members = self.client.get(reverse("entradas_api:admin_list"), {"section": "members"})
        self.assertEqual(access.status_code, 200)
        self.assertEqual(members.status_code, 403)

    def test_only_superuser_can_create_staff_and_choose_permissions(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.post(reverse("entradas_api:admin_staff"), {
            "name": "Operador Pedidos", "email": "pedidos@nkata.test",
            "password": "uma-senha-forte", "capabilities": ["access"],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        operator = User.objects.get(email="pedidos@nkata.test")
        self.assertTrue(operator.is_staff)
        self.assertFalse(hasattr(operator, "perfil_nkata"))
        self.assertEqual(response.data["staff"]["capabilities"], ["access"])

    def test_panel_shows_and_changes_member_plan(self):
        set_admin_capabilities(self.staff, ["members"])
        self.client.force_authenticate(self.staff)
        listing = self.client.get(reverse("entradas_api:admin_list"), {"section": "members"})
        self.assertEqual(listing.data["results"][0]["plan_code"], "LIVRE")
        change = self.client.post(reverse("entradas_api:admin_action"), {
            "resource": "member", "action": "plan_premium", "id": self.profile.id,
        }, format="json")
        self.assertEqual(change.status_code, 200)
        self.assertEqual(plan_code_for_user(self.member), "PREMIUM")

    def test_member_can_publish_predefined_text_moment(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(
            reverse("entradas_api:momentos"),
            {"caption": "BOAS_ENERGIAS"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        moment = MomentoNKATA.objects.get(pk=response.data["id"])
        self.assertEqual(moment.moderacao_status, "APROVADO")
        self.assertIsNotNone(moment.moderado_em)

    def test_member_can_pause_reactivate_and_request_closure(self):
        self.client.force_authenticate(self.member)
        pause = self.client.post(reverse("entradas_api:gestao_da_conta"), {
            "action": "pause", "days": 30, "reason": "Preciso de uma pausa.",
        }, format="json")
        self.assertEqual(pause.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, "PAUSADO")
        self.assertFalse(self.profile.visivel)

        reactivate = self.client.post(reverse("entradas_api:gestao_da_conta"), {
            "action": "reactivate",
        }, format="json")
        self.assertEqual(reactivate.status_code, 200)

        close = self.client.post(reverse("entradas_api:gestao_da_conta"), {
            "action": "close", "reason": "Já não quero usar a comunidade.",
            "password": "senha-segura",
        }, format="json")
        self.assertEqual(close.status_code, 200)
        self.profile.refresh_from_db()
        self.member.refresh_from_db()
        self.assertEqual(self.profile.status, "ENCERRAMENTO")
        self.assertFalse(self.member.is_active)

    def test_technical_system_state_is_superuser_only(self):
        set_admin_capabilities(self.staff, ["overview"])
        self.client.force_authenticate(self.staff)
        staff_response = self.client.get(reverse("entradas_api:admin_summary"))
        self.assertIsNone(staff_response.data["system"])
        self.client.force_authenticate(self.superuser)
        root_response = self.client.get(reverse("entradas_api:admin_summary"))
        self.assertIsInstance(root_response.data["system"], dict)
