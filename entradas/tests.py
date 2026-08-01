import json
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import (
    AcaoPerfil,
    MatchPerfil,
    MensagemMatch,
    PedidoEntrada,
    PerfilNKATA,
)


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="nkata-tests-")


def uploaded_file(name):
    return SimpleUploadedFile(name, b"nkata-test-file", content_type="image/jpeg")


def valid_image_file(name="perfil.jpg", size=(700, 700), image_format="JPEG"):
    stream = BytesIO()
    Image.new("RGB", size, color=(126, 38, 56)).save(stream, format=image_format)
    stream.seek(0)
    content_type = "image/png" if image_format == "PNG" else "image/jpeg"
    return SimpleUploadedFile(name, stream.read(), content_type=content_type)


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

    def test_conta_exige_login(self):
        response = self.client.get("/api/minha-conta/")
        self.assertIn(response.status_code, [401, 403])

    def test_conta_apresenta_dados_e_totais(self):
        user, perfil = self.create_profile("conta@example.com", "Conta")
        _, perfil_alvo = self.create_profile("conta-alvo@example.com", "Alvo")
        AcaoPerfil.objects.create(
            perfil=perfil_alvo,
            usuario=user,
            tipo="INTERESSE",
            session_key="sessao-conta",
        )
        MatchPerfil.objects.create(perfil_1=perfil, perfil_2=perfil_alvo)

        self.client.force_login(user)
        response = self.client.get("/api/minha-conta/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nome_publico"], "Conta")
        self.assertEqual(response.json()["email"], "conta@example.com")
        self.assertEqual(response.json()["total_matches"], 1)
        self.assertEqual(response.json()["total_interesses_enviados"], 1)

    def test_conta_pode_ser_editada_e_ocultada(self):
        user, perfil = self.create_profile("editar@example.com", "Nome Antigo")
        self.client.force_login(user)

        response = self.client.patch(
            "/api/minha-conta/",
            data=json.dumps({
                "nome_publico": "Nome Novo",
                "cidade": "Vilankulo",
                "objetivo": "CASAMENTO_FUTURO",
                "sobre_si": "Sou uma pessoa tranquila, responsável e gosto de conversar com sinceridade.",
                "visivel": False,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        perfil.refresh_from_db()
        user.refresh_from_db()
        self.assertEqual(perfil.nome_publico, "Nome Novo")
        self.assertEqual(perfil.cidade, "Vilankulo")
        self.assertEqual(perfil.objetivo, "CASAMENTO_FUTURO")
        self.assertFalse(perfil.visivel)
        self.assertEqual(user.first_name, "Nome Novo")

    def test_conta_rejeita_texto_sem_sentido(self):
        user, perfil = self.create_profile("texto@example.com", "Pessoa")
        self.client.force_login(user)

        response = self.client.patch(
            "/api/minha-conta/",
            data=json.dumps({
                "sobre_si": "jhj jjj dffd jkjd jdfd jkjd jfdj jdfj",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("sobre_si", response.json())
        perfil.refresh_from_db()
        self.assertEqual(perfil.sobre_si, "Gosto de conversas simples e sinceras.")

    def test_foto_perfil_pode_ser_atualizada(self):
        user, perfil = self.create_profile("foto@example.com", "Fotografia")
        nome_anterior = perfil.pedido.foto_perfil.name
        self.client.force_login(user)

        response = self.client.post(
            "/api/minha-conta/foto/",
            data={"foto": valid_image_file()},
        )

        self.assertEqual(response.status_code, 200)
        perfil.pedido.refresh_from_db()
        self.assertNotEqual(perfil.pedido.foto_perfil.name, nome_anterior)
        self.assertIn("account", response.json())
        self.assertTrue(response.json()["account"]["foto_principal"])

    def test_foto_pequena_e_rejeitada(self):
        user, perfil = self.create_profile("foto-pequena@example.com", "Fotografia")
        nome_anterior = perfil.pedido.foto_perfil.name
        self.client.force_login(user)

        response = self.client.post(
            "/api/minha-conta/foto/",
            data={"foto": valid_image_file(size=(300, 300))},
        )

        self.assertEqual(response.status_code, 400)
        perfil.pedido.refresh_from_db()
        self.assertEqual(perfil.pedido.foto_perfil.name, nome_anterior)

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

    def test_lista_de_matches_mostra_o_outro_perfil(self):
        user_a, perfil_a = self.create_profile("lista-a@example.com", "Pessoa A")
        _, perfil_b = self.create_profile("lista-b@example.com", "Pessoa B", city="Beira")
        MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_a)
        response = self.client.get("/api/minha-conta/matches/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["outro_perfil"]["id"],
            perfil_b.id,
        )

    def test_conversa_nao_pode_ser_aberta_por_terceiros(self):
        _, perfil_a = self.create_profile("conversa-a@example.com", "Pessoa A")
        _, perfil_b = self.create_profile("conversa-b@example.com", "Pessoa B")
        user_c, _ = self.create_profile("conversa-c@example.com", "Pessoa C")
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_c)
        response = self.client.get(
            f"/api/minha-conta/matches/{match.id}/conversa/"
        )

        self.assertEqual(response.status_code, 404)

    def test_mensagem_pode_ser_enviada_e_marcada_como_lida(self):
        user_a, perfil_a = self.create_profile("msg-a@example.com", "Pessoa A")
        user_b, perfil_b = self.create_profile("msg-b@example.com", "Pessoa B")
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_a)
        enviar = self.client.post(
            f"/api/minha-conta/matches/{match.id}/conversa/",
            data=json.dumps({"texto": "Olá, tudo bem?"}),
            content_type="application/json",
        )

        self.assertEqual(enviar.status_code, 201)
        self.assertTrue(enviar.json()["minha"])
        self.assertFalse(enviar.json()["lida"])

        self.client.force_login(user_b)
        abrir = self.client.get(
            f"/api/minha-conta/matches/{match.id}/conversa/"
        )

        self.assertEqual(abrir.status_code, 200)
        self.assertEqual(len(abrir.json()["results"]), 1)
        self.assertFalse(abrir.json()["results"][0]["minha"])
        self.assertTrue(abrir.json()["results"][0]["lida"])
        self.assertTrue(MensagemMatch.objects.get().lida)

    def test_mensagem_vazia_e_rejeitada(self):
        user_a, perfil_a = self.create_profile("vazia-a@example.com", "Pessoa A")
        _, perfil_b = self.create_profile("vazia-b@example.com", "Pessoa B")
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_a)
        response = self.client.post(
            f"/api/minha-conta/matches/{match.id}/conversa/",
            data=json.dumps({"texto": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(MensagemMatch.objects.count(), 0)
