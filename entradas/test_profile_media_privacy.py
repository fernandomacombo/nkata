from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import PedidoEntrada, PerfilNKATA, QuestionarioEntrada


def uploaded_file(name):
    return SimpleUploadedFile(name, b"nkata-private-media", content_type="image/jpeg")


class ProfileMediaPrivacyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="media-owner",
            email="owner@example.com",
            password="SenhaForte123",
        )
        self.member = User.objects.create_user(
            username="media-member",
            email="member@example.com",
            password="SenhaForte123",
        )
        self.staff = User.objects.create_user(
            username="media-staff",
            email="staff@example.com",
            password="SenhaForte123",
            is_staff=True,
        )
        self.pedido = PedidoEntrada.objects.create(
            nome_completo="Pessoa Protegida",
            email="protected@example.com",
            telefone="840000000",
            idade=30,
            cidade="Maputo",
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=uploaded_file("perfil-protegido.jpg"),
            foto_extra_1=uploaded_file("extra-1-protegido.jpg"),
            foto_extra_2=uploaded_file("extra-2-protegido.jpg"),
            foto_extra_3=uploaded_file("extra-3-protegido.jpg"),
            bi_frente=uploaded_file("bi-frente-protegido.jpg"),
            bi_verso=uploaded_file("bi-verso-protegido.jpg"),
            selfie_com_bi=uploaded_file("selfie-bi-protegido.jpg"),
            status="APROVADO",
        )
        QuestionarioEntrada.objects.create(
            pedido=self.pedido,
            disponibilidade="SIM",
            tem_filhos="NAO",
            aceita_pessoa_com_filhos="SIM",
            cidade_preferida="Maputo",
            faixa_etaria_preferida="25 a 40 anos",
            sobre_si="Procuro conhecer alguém com calma e intenção.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            aceita_regras=True,
        )
        self.perfil = PerfilNKATA.objects.create(
            pedido=self.pedido,
            usuario=self.owner,
            nome_publico="Pessoa",
            cidade="Maputo",
            idade=30,
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Perfil visível somente para membros autenticados.",
            o_que_valoriza="Respeito e compromisso.",
            o_que_nao_aceita="Desrespeito.",
            status="ATIVO",
            visivel=True,
        )

    def tearDown(self):
        for field_name in (
            "foto_perfil",
            "foto_extra_1",
            "foto_extra_2",
            "foto_extra_3",
            "bi_frente",
            "bi_verso",
            "selfie_com_bi",
        ):
            getattr(self.pedido, field_name).delete(save=False)

    def test_profiles_and_photo_require_authentication(self):
        list_response = self.client.get("/api/perfis/")
        photo_response = self.client.get(f"/api/perfis/{self.perfil.id}/foto/")

        self.assertIn(list_response.status_code, (401, 403))
        self.assertIn(photo_response.status_code, (401, 403))

    def test_authenticated_member_can_stream_visible_profile_photo(self):
        self.client.force_login(self.member)
        response = self.client.get(f"/api/perfis/{self.perfil.id}/foto/")
        try:
            self.assertEqual(
                response.status_code,
                200,
                (getattr(response, "data", None), dict(response.items())),
            )
            self.assertEqual(response["Cache-Control"], "private, max-age=300")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        finally:
            response.close()

    def test_identity_document_is_available_only_to_staff(self):
        url = f"/api/admin/pedidos/{self.pedido.id}/media/bi_frente/"

        self.client.force_login(self.member)
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403)

        self.client.force_login(self.staff)
        allowed = self.client.get(url)
        try:
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(allowed["Cache-Control"], "no-store")
        finally:
            allowed.close()

    def test_generic_media_url_is_not_served(self):
        with self.assertRaises(ValueError):
            _unused = self.pedido.bi_frente.url

        url = f"/media/{self.pedido.bi_frente.name}"
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            404,
            (url, response.__class__.__name__, dict(response.items())),
        )
