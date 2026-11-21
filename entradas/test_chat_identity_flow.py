from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from .identity_api import _live_capture_proof
from .identity_models import VerificacaoIdentidadeNKATA
from .models import AcessoPlanoNKATA, MatchPerfil, PedidoEntrada, PerfilNKATA, QuestionarioEntrada
from .test_access_status_api import image_file
from .test_identity_verification import accepted_result, textured_image


class ChatIdentityFlowTests(TestCase):
    def test_two_photos_then_entry_then_identity_then_chat(self):
        response = self.client.post("/api/pedir-acesso/", {
            "nome_completo": "Pessoa Nova",
            "email": "pessoa@example.com",
            "telefone": "+258850000009",
            "numero_bi": "110100000009A",
            "idade": 29,
            "cidade": "Maputo",
            "genero": "FEMININO",
            "objetivo": "RELACIONAMENTO_SERIO",
            "aceita_verificacao": "on",
            "foto_perfil": image_file("perfil.jpg"),
            "foto_extra_1": image_file("outra-foto.jpg"),
        })
        self.assertEqual(response.status_code, 201, response.json())
        pedido = PedidoEntrada.objects.get(email="pessoa@example.com")
        self.assertTrue(pedido.verificacao_apos_entrada)
        self.assertFalse(pedido.documento_confirmado)
        self.assertFalse(pedido.foto_extra_2)

        operator = User.objects.create_superuser("reviewer")
        self.client.force_login(operator)
        action_url = "/api/painel/acoes/"
        decision = {"resource": "access", "id": pedido.id}
        response = self.client.post(action_url, {**decision, "action": "approve_entry"})
        self.assertEqual(response.status_code, 200, response.json())
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, "APROVADO")

        questionario = f"/api/questionario/{pedido.token}/"
        response = self.client.post(questionario, {
            "disponibilidade": "SIM",
            "tem_filhos": "NAO",
            "aceita_pessoa_com_filhos": "SIM",
            "cidade_preferida": "Maputo",
            "faixa_etaria_preferida": "25 a 35 anos",
            "sobre_si": "Gosto de ler e caminhar ao fim da tarde.",
            "o_que_valoriza": "Respeito e boa comunicação.",
            "o_que_nao_aceita": "Falta de respeito.",
            "aceita_regras": "on",
        })
        self.assertEqual(response.status_code, 200, response.json())
        password = "Test!ChatIdentity#47"
        response = self.client.post(f"{questionario}criar-senha/", {
            "password": password,
            "confirmation": password,
        })
        self.assertEqual(response.status_code, 200, response.json())
        member = PerfilNKATA.objects.get(pedido=pedido)
        self.assertEqual(member.status, "ATIVO")
        self.assertTrue(response.json()["promotion_granted"])
        access = AcessoPlanoNKATA.objects.get(usuario=member.usuario)
        self.assertEqual(access.plano, "QUINZENAL")
        self.assertEqual((access.fim - access.inicio).days, 15)

        other = PedidoEntrada.objects.create(
            email="other@example.com", nome_completo="Outro Membro", telefone="+258840000099",
            idade=30, cidade="Maputo", genero="MASCULINO", objetivo="RELACIONAMENTO_SERIO",
            status="APROVADO",
        )
        QuestionarioEntrada.objects.create(pedido=other)
        other_user = User.objects.create_user("other-member", password=password)
        other_profile = PerfilNKATA.objects.create(
            pedido=other, usuario=other_user, nome_publico="Outro Membro",
            cidade="Maputo", idade=30, objetivo="RELACIONAMENTO_SERIO", status="ATIVO",
        )
        match = MatchPerfil.objects.create(
            perfil_1=member, perfil_2=other_profile, status="ATIVO",
        )
        self.client.force_login(member.usuario)
        match_url = f"/api/minha-conta/matches/{match.id}/"
        for suffix in ("conversa/", "audio/", "audio/1/media/", "live/", "call/", "calls/history/"):
            with self.subTest(endpoint=suffix):
                self.assertEqual(self.client.get(f"{match_url}{suffix}").status_code, 403)
        self.assertEqual(self.client.post(f"{match_url}conversa/", {"texto": "Olá"}).status_code, 403)
        self.assertTrue(self.client.get("/api/session/").json()["profile"]["chat_identity_required"])

        identity_url = "/api/minha-conta/nkata-id/"
        response = self.client.post(identity_url, {"aceita_biometria": True}, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.json())
        token = response.json()["token"]
        self.assertEqual(self.client.get(identity_url).json()["token"], token)
        verification = VerificacaoIdentidadeNKATA.objects.get(pedido=pedido)
        with patch("entradas.identity_api.inspect_identity_capture", side_effect=lambda image, kind: accepted_result(kind)):
            for kind in VerificacaoIdentidadeNKATA.CAPTURE_FIELDS:
                response = self.client.post(f"/api/nkata-id/sessoes/{token}/capturas/{kind}/", {
                    "imagem": textured_image(f"{kind}.jpg"),
                    "live_capture_proof": _live_capture_proof(verification, kind),
                })
                self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(response.json()["status"], "REVISAO")
        self.assertEqual(self.client.get(f"{match_url}conversa/").status_code, 403)

        self.client.force_login(operator)
        response = self.client.post(action_url, {
            **decision, "action": "approve", "document_number": "110100000009A",
        })
        self.assertEqual(response.status_code, 200, response.json())
        self.client.force_login(member.usuario)
        self.assertFalse(self.client.get("/api/session/").json()["profile"]["chat_identity_required"])
        self.assertEqual(self.client.get(f"{match_url}conversa/").status_code, 200)
