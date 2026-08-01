import json
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import AcaoPerfil, MatchPerfil, PedidoEntrada, PerfilNKATA


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="nkata-tests-")


def uploaded_file(name):
    return SimpleUploadedFile(name, b"nkata-test-file", content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class NkataApiTests(TestCase):
    def create_profile(self, email, name, city="Maputo"):
        user = User.objects.create_user(
            username=email.split("@")[0],
            email=email,
            password="SenhaForte123",
            first_name=name,
        )
        pedido = PedidoEntrada.objects.create(
            nome_completo=name,
            email=email,
            telefone="840000000",
            idade=30,
            cidade=city,
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=uploaded_file(f"{name}-perfil.jpg"),
            foto_extra_1=uploaded_file(f"{name}-extra-1.jpg"),
            foto_extra_2=uploaded_file(f"{name}-extra-2.jpg"),
            foto_extra_3=uploaded_file(f"{name}-extra-3.jpg"),
            bi_frente=uploaded_file(f"{name}-bi-frente.jpg"),
            bi_verso=uploaded_file(f"{name}-bi-verso.jpg"),
            selfie_com_bi=uploaded_file(f"{name}-selfie.jpg"),
            status="APROVADO",
        )
        perfil = PerfilNKATA.objects.create(
            pedido=pedido,
            usuario=user,
            nome_publico=name,
            cidade=city,
            idade=30,
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Gosto de conversas simples e sinceras.",
            o_que_valoriza="Respeito e honestidade.",
            o_que_nao_aceita="Desrespeito.",
            status="ATIVO",
            visivel=True,
        )
        return user, perfil

    def test_login_com_email(self):
        user, perfil = self.create_profile("fernando@example.com", "Fernando")

        response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({
                "email": "fernando@example.com",
                "password": "SenhaForte123",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["id"], user.id)
        self.assertEqual(response.json()["profile"]["id"], perfil.id)

    def test_interesse_exige_login(self):
        _, perfil = self.create_profile("alvo@example.com", "Alvo")

        response = self.client.post(f"/api/perfis/{perfil.id}/interesse/")

        self.assertIn(response.status_code, [401, 403])

    def test_interesse_pode_ser_adicionado_e_removido(self):
        user, _ = self.create_profile("origem@example.com", "Origem")
        _, perfil_alvo = self.create_profile("destino@example.com", "Destino")
        self.client.force_login(user)

        adicionar = self.client.post(f"/api/perfis/{perfil_alvo.id}/interesse/")
        remover = self.client.post(f"/api/perfis/{perfil_alvo.id}/interesse/")

        self.assertEqual(adicionar.status_code, 200)
        self.assertTrue(adicionar.json()["active"])
        self.assertEqual(remover.status_code, 200)
        self.assertFalse(remover.json()["active"])
        self.assertFalse(
            AcaoPerfil.objects.filter(
                perfil=perfil_alvo,
                usuario=user,
                tipo="INTERESSE",
            ).exists()
        )

    def test_interesse_mutuo_cria_match(self):
        user_a, perfil_a = self.create_profile("a@example.com", "Pessoa A")
        user_b, perfil_b = self.create_profile("b@example.com", "Pessoa B")

        AcaoPerfil.objects.create(
            perfil=perfil_a,
            usuario=user_b,
            tipo="INTERESSE",
            session_key="sessao-pessoa-b",
        )

        self.client.force_login(user_a)
        response = self.client.post(f"/api/perfis/{perfil_b.id}/interesse/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["match"])
        self.assertEqual(MatchPerfil.objects.count(), 1)
