import json
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import AcaoPerfil, MatchPerfil, MensagemMatch, PedidoEntrada, PerfilNKATA
from .notification_models import NotificacaoNKATA


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="nkata-notification-tests-")


def uploaded_file(name):
    return SimpleUploadedFile(name, b"nkata-notification-test", content_type="image/jpeg")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class NkataNotificationApiTests(TestCase):
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

    def test_interesse_cria_notificacao_para_o_perfil_destino(self):
        user_a, _ = self.create_profile("interesse-a@example.com", "Amélia")
        user_b, perfil_b = self.create_profile("interesse-b@example.com", "Bento")

        AcaoPerfil.objects.create(
            perfil=perfil_b,
            usuario=user_a,
            tipo="INTERESSE",
            session_key="interesse-a-b",
        )

        notificacao = NotificacaoNKATA.objects.get(destinatario=user_b)
        self.assertEqual(notificacao.tipo, "INTERESSE")
        self.assertEqual(notificacao.perfil, user_a.perfil_nkata)
        self.assertFalse(notificacao.lida)

    def test_match_cria_um_aviso_para_cada_pessoa(self):
        user_a, perfil_a = self.create_profile("match-a@example.com", "Ana")
        user_b, perfil_b = self.create_profile("match-b@example.com", "Bruno")

        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.assertTrue(
            NotificacaoNKATA.objects.filter(
                destinatario=user_a,
                match=match,
                tipo="MATCH",
            ).exists()
        )
        self.assertTrue(
            NotificacaoNKATA.objects.filter(
                destinatario=user_b,
                match=match,
                tipo="MATCH",
            ).exists()
        )

    def test_mensagens_do_mesmo_match_atualizam_um_unico_aviso(self):
        user_a, perfil_a = self.create_profile("mensagem-a@example.com", "Alice")
        user_b, perfil_b = self.create_profile("mensagem-b@example.com", "Bernardo")
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        NotificacaoNKATA.objects.filter(tipo="MATCH").delete()

        MensagemMatch.objects.create(
            match=match,
            remetente=user_a,
            texto="Olá, gostei muito da sua apresentação.",
        )
        MensagemMatch.objects.create(
            match=match,
            remetente=user_a,
            texto="Como foi o seu dia?",
        )

        avisos = NotificacaoNKATA.objects.filter(
            destinatario=user_b,
            match=match,
            tipo="MENSAGEM",
        )
        self.assertEqual(avisos.count(), 1)
        self.assertEqual(avisos.get().texto, "Como foi o seu dia?")
        self.assertFalse(avisos.get().lida)

    def test_api_lista_e_marca_notificacoes_como_lidas(self):
        user_a, perfil_a = self.create_profile("api-a@example.com", "Alda")
        user_b, perfil_b = self.create_profile("api-b@example.com", "Basilio")
        match = MatchPerfil.objects.create(perfil_1=perfil_a, perfil_2=perfil_b)

        self.client.force_login(user_a)
        lista = self.client.get("/api/minha-conta/notificacoes/")

        self.assertEqual(lista.status_code, 200)
        self.assertEqual(lista.json()["unread"], 1)
        notificacao_id = lista.json()["results"][0]["id"]

        lida = self.client.post(
            f"/api/minha-conta/notificacoes/{notificacao_id}/ler/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(lida.status_code, 200)
        self.assertTrue(NotificacaoNKATA.objects.get(id=notificacao_id).lida)

        NotificacaoNKATA.objects.create(
            destinatario=user_a,
            perfil=perfil_b,
            match=match,
            tipo="EQUIPA",
            titulo="Um aviso da equipa",
            texto="A sua conta foi revista.",
            chave="equipa:teste",
        )
        todas = self.client.post(
            "/api/minha-conta/notificacoes/marcar-todas-lidas/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(todas.status_code, 200)
        self.assertFalse(
            NotificacaoNKATA.objects.filter(
                destinatario=user_a,
                lida=False,
            ).exists()
        )
