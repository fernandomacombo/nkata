from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .admin_panel_api import _admin_call_duration_seconds, _admin_call_status
from .call_models import ChamadaMatchNKATA
from .identity_models import VerificacaoIdentidadeNKATA
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

        detail = self.client.get(
            reverse(
                "entradas_api:admin_access_detail",
                kwargs={"pedido_id": self.request_record.id},
            )
        )
        self.assertEqual(detail.status_code, 403)

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
        self.assertEqual(members.data["results"][0]["gender_label"], "Feminino")
        self.assertEqual(
            members.data["results"][0]["objective_label"],
            "Relacionamento sério",
        )

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

        audit = self.client.get(
            reverse("entradas_api:admin_list"),
            {"section": "audit", "status": "ALTERACAO"},
        )
        self.assertEqual(audit.status_code, 200)
        self.assertEqual(audit.data["total"], 1)
        entry = audit.data["results"][0]
        self.assertEqual(entry["operation_type"], "AUDIT")
        self.assertEqual(entry["status"], "ALTERACAO")
        self.assertEqual(entry["operator"], self.staff.email)
        self.assertIn("Membro pausado", entry["detail"])

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

    def test_staff_can_review_private_identity_evidence_in_panel(self):
        pending = create_request("identidade@nkata.test", status="PENDENTE")
        verification = VerificacaoIdentidadeNKATA.objects.create(
            pedido=pending,
            email_hash="a" * 64,
            idade_declarada=pending.idade,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto para a direita.",
            status="REVISAO",
            risco="MEDIO",
            pontuacao_risco=35,
            bi_frente="nkata-id/documentos/frente.jpg",
            bi_verso="nkata-id/documentos/verso.jpg",
            selfie_ao_vivo="nkata-id/selfies/frontal.jpg",
            selfie_desafio="nkata-id/selfies/desafio.jpg",
            vivacidade_confirmada=True,
            verificacoes_imagem={
                "bi_frente": {"accepted": True, "score": 94, "messages": []},
                "bi_verso": {"accepted": True, "score": 92, "messages": []},
                "selfie_ao_vivo": {"accepted": True, "score": 96, "messages": []},
                "selfie_desafio": {"accepted": True, "score": 95, "messages": []},
            },
            sinais_risco={
                "documento_reutilizado": False,
                "sequencia_ao_vivo": True,
                "selfies_diferentes": True,
                "comparacao_facial_disponivel": False,
            },
        )
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            reverse(
                "entradas_api:admin_access_detail",
                kwargs={"pedido_id": pending.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["profile_media"]), 4)
        self.assertEqual(len(response.data["identity_media"]), 4)
        self.assertTrue(all(item["available"] for item in response.data["identity_media"]))
        self.assertEqual(response.data["identity"]["id"], verification.id)
        self.assertEqual(response.data["identity"]["status"], "REVISAO")
        self.assertTrue(response.data["identity"]["liveness_confirmed"])
        self.assertNotIn("documento_sha256", response.data["identity"])

    def test_approving_reviewed_nkata_id_approves_identity_and_request(self):
        pending = create_request("decisao@nkata.test", status="EM_ANALISE")
        verification = VerificacaoIdentidadeNKATA.objects.create(
            pedido=pending,
            email_hash="b" * 64,
            idade_declarada=pending.idade,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto.",
            status="REVISAO",
            bi_frente="nkata-id/documentos/frente.jpg",
            bi_verso="nkata-id/documentos/verso.jpg",
            selfie_ao_vivo="nkata-id/selfies/frontal.jpg",
            selfie_desafio="nkata-id/selfies/desafio.jpg",
        )
        self.client.force_authenticate(self.staff)

        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {"resource": "access", "action": "approve", "id": pending.id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(pending.status, "APROVADO")
        self.assertEqual(verification.status, "APROVADA")
        self.assertEqual(verification.decisao_origem, "HUMANA")
        self.assertEqual(verification.analisado_por, self.staff)

    def test_incomplete_nkata_id_cannot_be_approved(self):
        pending = create_request("incompleto@nkata.test", status="PENDENTE")
        VerificacaoIdentidadeNKATA.objects.create(
            pedido=pending,
            email_hash="c" * 64,
            idade_declarada=pending.idade,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto.",
            status="REVISAO",
        )
        self.client.force_authenticate(self.staff)

        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {"resource": "access", "action": "approve", "id": pending.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        pending.refresh_from_db()
        self.assertEqual(pending.status, "PENDENTE")

    def test_rejection_requires_an_internal_reason(self):
        pending = create_request("motivo@nkata.test", status="EM_ANALISE")
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {"resource": "access", "action": "reject", "id": pending.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        pending.refresh_from_db()
        self.assertEqual(pending.status, "EM_ANALISE")

    def test_requesting_new_captures_resets_identity_safely(self):
        reason = "A selfie está desfocada; repetir todas as capturas."
        pending = create_request("repetir@nkata.test", status="EM_ANALISE")
        verification = VerificacaoIdentidadeNKATA.objects.create(
            pedido=pending,
            email_hash="e" * 64,
            idade_declarada=pending.idade,
            aceita_biometria=True,
            desafio_selfie="Vire o rosto.",
            status="REVISAO",
            bi_frente="nkata-id/documentos/frente.jpg",
            bi_verso="nkata-id/documentos/verso.jpg",
            selfie_ao_vivo="nkata-id/selfies/frontal.jpg",
            selfie_desafio="nkata-id/selfies/desafio.jpg",
            vivacidade_confirmada=True,
            pontuacao_risco=35,
        )
        self.client.force_authenticate(self.staff)

        response = self.client.post(
            reverse("entradas_api:admin_action"),
            {
                "resource": "access",
                "action": "correction",
                "id": pending.id,
                "note": reason,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        verification.refresh_from_db()
        self.assertEqual(pending.status, "PRECISA_CORRIGIR")
        self.assertEqual(verification.status, "REPETIR")
        self.assertFalse(verification.capturas_completas)
        self.assertFalse(verification.vivacidade_confirmada)
        self.assertEqual(verification.pontuacao_risco, 0)
        self.assertEqual(verification.nota_interna, reason)

    def test_questionnaire_link_is_exposed_only_for_approved_pending_response(self):
        waiting = create_request("aguarda@nkata.test", status="APROVADO")
        pending = create_request("pendente@nkata.test", status="PENDENTE")
        self.client.force_authenticate(self.staff)

        response = self.client.get(
            reverse("entradas_api:admin_list"),
            {"section": "access"},
        )

        self.assertEqual(response.status_code, 200)
        rows = {item["email"]: item for item in response.data["results"]}
        self.assertEqual(
            rows[waiting.email]["questionnaire_path"],
            f"/questionario/{waiting.token}/",
        )
        self.assertEqual(rows[pending.email]["questionnaire_path"], "")
        self.assertEqual(
            rows[self.request_record.email]["questionnaire_path"],
            "",
        )

    def test_approved_request_with_identity_in_review_stays_in_work_queue(self):
        waiting = create_request("revisao-antiga@nkata.test", status="APROVADO")
        VerificacaoIdentidadeNKATA.objects.create(
            pedido=waiting,
            email_hash="f" * 64,
            idade_declarada=waiting.idade,
            aceita_biometria=True,
            desafio_selfie="Olhe para a câmara.",
            status="REVISAO",
            bi_frente="nkata-id/documentos/frente.jpg",
            bi_verso="nkata-id/documentos/verso.jpg",
            selfie_ao_vivo="nkata-id/selfies/frontal.jpg",
            selfie_desafio="nkata-id/selfies/desafio.jpg",
        )
        self.client.force_authenticate(self.staff)

        summary = self.client.get(reverse("entradas_api:admin_summary"))
        queue = self.client.get(
            reverse("entradas_api:admin_list"),
            {"section": "access", "status": "EM_ANALISE"},
        )
        detail = self.client.get(
            reverse(
                "entradas_api:admin_access_detail",
                kwargs={"pedido_id": waiting.id},
            )
        )

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["metrics"]["access_pending"], 1)
        self.assertEqual(queue.status_code, 200)
        row = next(item for item in queue.data["results"] if item["id"] == waiting.id)
        self.assertEqual(row["display_status"], "EM_ANALISE")
        self.assertEqual(row["display_status_label"], "Identidade pendente")
        self.assertEqual(row["questionnaire_path"], "")
        self.assertEqual(detail.data["display_status"], "EM_ANALISE")
        self.assertEqual(detail.data["questionnaire_path"], "")

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
