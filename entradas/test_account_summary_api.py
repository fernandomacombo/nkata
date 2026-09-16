from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from .call_models import ChamadaMatchNKATA
from .models import (
    AcaoPerfil,
    MatchPerfil,
    MensagemMatch,
    PedidoEntrada,
    PerfilNKATA,
    QuestionarioEntrada,
)
from .plan_service import assign_plan
from .posts_models import PublicacaoNKATA


def file_upload(name):
    return SimpleUploadedFile(name, b"nkata-summary-test", content_type="image/jpeg")


class AccountSummaryApiTests(TestCase):
    def setUp(self):
        self.owner, self.owner_profile = self._create_profile("summary-owner", "Marta")
        self.other, self.other_profile = self._create_profile("summary-other", "Carlos")
        PerfilNKATA.objects.filter(pk=self.owner_profile.pk).update(
            destaque_publico=True,
            destaque_publico_exibicoes=12,
        )

    def _create_profile(self, username, name):
        email = f"{username}@example.com"
        user = User.objects.create_user(
            username=username,
            email=email,
            password="SenhaForte123",
        )
        pedido = PedidoEntrada.objects.create(
            nome_completo=name,
            email=email,
            telefone=f"84{user.id:07d}",
            idade=30,
            cidade="Maputo",
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=file_upload(f"{username}-perfil.jpg"),
            bi_frente=file_upload(f"{username}-frente.jpg"),
            bi_verso=file_upload(f"{username}-verso.jpg"),
            selfie_com_bi=file_upload(f"{username}-selfie.jpg"),
            status="APROVADO",
        )
        QuestionarioEntrada.objects.create(
            pedido=pedido,
            disponibilidade="SIM",
            tem_filhos="NAO",
            aceita_pessoa_com_filhos="SIM",
            cidade_preferida="Maputo",
            faixa_etaria_preferida="25 a 40 anos",
            sobre_si="Procuro uma relação séria construída com respeito.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            aceita_regras=True,
        )
        perfil = PerfilNKATA.objects.create(
            pedido=pedido,
            usuario=user,
            nome_publico=name,
            cidade="Maputo",
            idade=30,
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Procuro uma relação séria construída com respeito.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            status="ATIVO",
            visivel=True,
        )
        return user, perfil

    def tearDown(self):
        for publication in PublicacaoNKATA.objects.all():
            if publication.media:
                publication.media.delete(save=False)
        for pedido in PedidoEntrada.objects.all():
            for field_name in ("foto_perfil", "bi_frente", "bi_verso", "selfie_com_bi"):
                field = getattr(pedido, field_name)
                if field:
                    field.delete(save=False)

    def test_summary_requires_authentication(self):
        response = self.client.get("/api/minha-conta/resumo/")
        self.assertIn(response.status_code, (401, 403))

    def test_summary_uses_real_account_activity_and_plan_quota(self):
        match = MatchPerfil.objects.create(
            perfil_1=self.owner_profile,
            perfil_2=self.other_profile,
            status="ATIVO",
        )
        for action_type, key in (
            ("INTERESSE", "interest"),
            ("SEGUIR", "follow"),
            ("GUARDADO", "saved"),
        ):
            AcaoPerfil.objects.create(
                perfil=self.owner_profile,
                usuario=self.other,
                tipo=action_type,
                session_key=key,
            )
        AcaoPerfil.objects.create(
            perfil=self.other_profile,
            usuario=self.owner,
            tipo="SINAL_FLOR",
            session_key="sinal:plano:summary",
        )
        MensagemMatch.objects.create(
            match=match,
            remetente=self.owner,
            texto="Olá, tudo bem?",
        )
        call = ChamadaMatchNKATA.objects.create(
            match=match,
            iniciador=self.owner,
            tipo="AUDIO",
            estado="TERMINADA",
        )
        ended = timezone.now()
        ChamadaMatchNKATA.objects.filter(pk=call.pk).update(
            atendida_em=ended - timedelta(seconds=90),
            terminada_em=ended,
        )
        PublicacaoNKATA.objects.create(
            perfil=self.owner_profile,
            usuario=self.owner,
            media=file_upload("summary-post.jpg"),
            tipo_media="IMAGEM",
            visibilidade="TODOS",
            moderacao_status="APROVADO",
        )
        assign_plan(self.owner, "PREMIUM")

        self.client.force_login(self.owner)
        response = self.client.get("/api/minha-conta/resumo/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["plan"]["code"], "PREMIUM")
        self.assertEqual(payload["plan"]["signal_quota"]["used_today"], 1)
        self.assertEqual(payload["performance"]["active_matches"], 1)
        self.assertEqual(payload["performance"]["interests_received"], 1)
        self.assertEqual(payload["performance"]["followers"], 1)
        self.assertEqual(payload["performance"]["saved_by_members"], 1)
        self.assertEqual(payload["performance"]["public_impressions"], 12)
        self.assertEqual(payload["activity"]["approved_publications"], 1)
        self.assertEqual(payload["activity"]["messages_sent"], 1)
        self.assertEqual(payload["activity"]["calls"]["total"], 1)
        self.assertEqual(payload["activity"]["calls"]["completed"], 1)
        self.assertEqual(payload["activity"]["calls"]["duration_seconds"], 90)
        self.assertNotIn("email", payload)
