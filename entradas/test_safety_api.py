import json
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import (
    AcaoPerfil,
    DenunciaPerfil,
    MatchPerfil,
    PedidoEntrada,
    PerfilNKATA,
)


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="nkata-safety-tests-")


def uploaded_file(name):
    return SimpleUploadedFile(name, b"nkata-safety-test", content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class NkataSafetyApiTests(TestCase):
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
            idade=32,
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
            idade=32,
            genero="MASCULINO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Procuro uma relação séria, tranquila e com respeito.",
            o_que_valoriza="Honestidade, diálogo e compromisso.",
            o_que_nao_aceita="Desrespeito e falta de sinceridade.",
            status="ATIVO",
            visivel=True,
        )
        return user, perfil

    def test_denuncia_fica_registada_e_nao_duplica_enquanto_aberta(self):
        user, _ = self.create_profile("denunciante@example.com", "Denunciante")
        _, perfil_alvo = self.create_profile("denunciado@example.com", "Denunciado")
        self.client.force_login(user)

        primeira = self.client.post(
            f"/api/perfis/{perfil_alvo.id}/denunciar/",
            data=json.dumps({
                "motivo": "COMPORTAMENTO_INADEQUADO",
                "detalhes": "Enviou mensagens ofensivas durante a conversa.",
            }),
            content_type="application/json",
        )
        repetida = self.client.post(
            f"/api/perfis/{perfil_alvo.id}/denunciar/",
            data=json.dumps({
                "motivo": "OUTRO",
                "detalhes": "Uma segunda denúncia ainda não deve ser criada.",
            }),
            content_type="application/json",
        )

        self.assertEqual(primeira.status_code, 201)
        self.assertEqual(repetida.status_code, 409)
        self.assertEqual(DenunciaPerfil.objects.count(), 1)
        self.assertEqual(DenunciaPerfil.objects.get().denunciante, user)

    def test_bloqueio_remove_interesses_encerra_match_e_esconde_perfis(self):
        user_a, perfil_a = self.create_profile("bloqueio-a@example.com", "Pessoa A")
        user_b, perfil_b = self.create_profile("bloqueio-b@example.com", "Pessoa B")

        AcaoPerfil.objects.create(
            perfil=perfil_b,
            usuario=user_a,
            tipo="INTERESSE",
            session_key="interesse-a",
        )
        AcaoPerfil.objects.create(
            perfil=perfil_a,
            usuario=user_b,
            tipo="INTERESSE",
            session_key="interesse-b",
        )
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_a)
        resposta = self.client.post(f"/api/perfis/{perfil_b.id}/bloquear/")

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(
            AcaoPerfil.objects.filter(
                perfil=perfil_b,
                usuario=user_a,
                tipo="BLOQUEIO",
            ).exists()
        )
        self.assertFalse(AcaoPerfil.objects.filter(tipo="INTERESSE").exists())

        match.refresh_from_db()
        self.assertEqual(match.status, "ENCERRADO")

        lista_a = self.client.get("/api/perfis/").json()["results"]
        self.assertNotIn(perfil_b.id, [item["id"] for item in lista_a])
        self.assertEqual(
            self.client.get(f"/api/perfis/{perfil_b.id}/").status_code,
            404,
        )

        self.client.force_login(user_b)
        lista_b = self.client.get("/api/perfis/").json()["results"]
        self.assertNotIn(perfil_a.id, [item["id"] for item in lista_b])
        self.assertEqual(
            self.client.get(f"/api/perfis/{perfil_a.id}/").status_code,
            404,
        )

        novo_interesse = self.client.post(f"/api/perfis/{perfil_a.id}/interesse/")
        self.assertEqual(novo_interesse.status_code, 403)

    def test_encerrar_ligacao_remove_match_da_lista_e_fecha_conversa(self):
        user_a, perfil_a = self.create_profile("encerrar-a@example.com", "Pessoa A")
        _, perfil_b = self.create_profile("encerrar-b@example.com", "Pessoa B")
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_a)
        resposta = self.client.post(
            f"/api/minha-conta/matches/{match.id}/encerrar/"
        )

        self.assertEqual(resposta.status_code, 200)
        match.refresh_from_db()
        self.assertEqual(match.status, "ENCERRADO")

        lista = self.client.get("/api/minha-conta/matches/")
        self.assertEqual(lista.status_code, 200)
        self.assertEqual(lista.json()["count"], 0)

        conversa = self.client.get(
            f"/api/minha-conta/matches/{match.id}/conversa/"
        )
        self.assertEqual(conversa.status_code, 404)
