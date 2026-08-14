from io import BytesIO

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import PedidoEntrada, PerfilNKATA, QuestionarioEntrada


def valid_image_file(name="perfil-publico.jpg"):
    buffer = BytesIO()
    Image.new("RGB", (600, 600), "#8b5d67").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class PublicProfilePreviewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="public-preview-owner",
            email="preview@example.com",
            password="SenhaForte123",
            first_name="Pessoa",
        )
        self.pedido = PedidoEntrada.objects.create(
            nome_completo="Pessoa Pública",
            email="preview@example.com",
            telefone="840000111",
            idade=31,
            cidade="Maputo",
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=valid_image_file(),
            bi_frente=valid_image_file("bi-frente.jpg"),
            bi_verso=valid_image_file("bi-verso.jpg"),
            selfie_com_bi=valid_image_file("selfie.jpg"),
            status="APROVADO",
        )
        QuestionarioEntrada.objects.create(
            pedido=self.pedido,
            disponibilidade="SIM",
            tem_filhos="NAO",
            aceita_pessoa_com_filhos="SIM",
            cidade_preferida="Maputo",
            faixa_etaria_preferida="28 a 40 anos",
            sobre_si="Procuro uma relação séria construída com respeito.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            aceita_regras=True,
        )
        self.perfil = PerfilNKATA.objects.create(
            pedido=self.pedido,
            usuario=self.owner,
            nome_publico="Pessoa",
            cidade="Maputo",
            idade=31,
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Procuro uma relação séria construída com respeito.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            status="ATIVO",
            visivel=True,
            foto_destaque_publico_aprovada=True,
        )

    def tearDown(self):
        for field_name in (
            "foto_perfil",
            "bi_frente",
            "bi_verso",
            "selfie_com_bi",
        ):
            field = getattr(self.pedido, field_name)
            if field:
                field.delete(save=False)

    def test_public_preview_is_opt_in_and_photo_is_closed_by_default(self):
        listing = self.client.get("/api/publico/perfis/")
        photo = self.client.get(f"/api/publico/perfis/{self.perfil.id}/foto/")

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["results"], [])
        self.assertEqual(photo.status_code, 404)

    def test_owner_can_consent_and_public_payload_stays_minimal(self):
        self.client.force_login(self.owner)
        consent = self.client.patch(
            "/api/minha-conta/",
            {"destaque_publico": True},
            content_type="application/json",
        )
        self.assertEqual(consent.status_code, 200, consent.json())
        self.assertTrue(consent.json()["destaque_publico"])
        self.assertIsNotNone(consent.json()["destaque_publico_consentido_em"])

        self.client.logout()
        listing = self.client.get("/api/publico/perfis/")
        self.assertEqual(listing.status_code, 200)
        result = listing.json()["results"][0]
        self.assertEqual(result["id"], self.perfil.id)
        self.assertNotIn("email", result)
        self.assertNotIn("sobre_si", result)
        self.assertNotIn("o_que_valoriza", result)

        photo = self.client.get(result["foto_principal"])
        try:
            self.assertEqual(photo.status_code, 200)
            self.assertEqual(photo["Cache-Control"], "no-store")
            self.assertIn("noimageindex", photo["X-Robots-Tag"])
        finally:
            photo.close()

        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.destaque_publico_exibicoes, 1)
        self.assertIsNotNone(self.perfil.destaque_publico_ultima_exibicao_em)

    def test_disabling_consent_removes_photo_immediately(self):
        PerfilNKATA.objects.filter(pk=self.perfil.pk).update(destaque_publico=True)

        self.client.force_login(self.owner)
        response = self.client.patch(
            "/api/minha-conta/",
            {"destaque_publico": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.assertEqual(
            self.client.get(f"/api/publico/perfis/{self.perfil.id}/foto/").status_code,
            404,
        )
        self.assertEqual(self.client.get("/api/publico/perfis/").json()["results"], [])

    def test_unapproved_photo_cannot_be_published(self):
        self.perfil.foto_destaque_publico_aprovada = False
        self.perfil.save(update_fields=["foto_destaque_publico_aprovada"])
        self.client.force_login(self.owner)

        response = self.client.patch(
            "/api/minha-conta/",
            {"destaque_publico": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("destaque_publico", response.json())

    def test_new_profile_photo_disables_public_preview_until_review(self):
        PerfilNKATA.objects.filter(pk=self.perfil.pk).update(destaque_publico=True)
        self.client.force_login(self.owner)

        response = self.client.post(
            "/api/minha-conta/foto/",
            {"foto": valid_image_file("nova-foto.jpg")},
        )

        self.assertEqual(response.status_code, 200, response.json())
        self.perfil.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertFalse(self.perfil.destaque_publico)
        self.assertFalse(self.perfil.foto_destaque_publico_aprovada)
