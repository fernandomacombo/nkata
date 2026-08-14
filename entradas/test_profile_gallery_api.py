from io import BytesIO

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import MatchPerfil, PedidoEntrada, PerfilNKATA, QuestionarioEntrada
from .posts_models import PublicacaoNKATA


def image_file(name="gallery.jpg"):
    stream = BytesIO()
    Image.new("RGB", (700, 500), "#6f4a52").save(stream, format="JPEG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/jpeg")


def video_file(name="gallery.mp4"):
    return SimpleUploadedFile(name, b"nkata-video-test", content_type="video/mp4")


class ProfileGalleryApiTests(TestCase):
    def setUp(self):
        self.owner, self.owner_profile = self._create_profile("owner", "Marta")
        self.viewer, self.viewer_profile = self._create_profile("viewer", "Carlos")

        self.cover_post = self._create_post(
            "IMAGEM",
            image_file("cover.jpg"),
            visibility="TODOS",
        )
        self.matches_post = self._create_post(
            "IMAGEM",
            image_file("matches.jpg"),
            visibility="MATCHES",
        )
        self.video_post = self._create_post(
            "VIDEO",
            video_file(),
            visibility="TODOS",
        )
        self.pending_post = self._create_post(
            "IMAGEM",
            image_file("pending.jpg"),
            visibility="TODOS",
            status="PENDENTE",
        )

    def _create_profile(self, suffix, name):
        email = f"gallery-{suffix}@example.com"
        user = User.objects.create_user(
            username=f"gallery-{suffix}",
            email=email,
            password="SenhaForte123",
            first_name=name,
        )
        pedido = PedidoEntrada.objects.create(
            nome_completo=name,
            email=email,
            telefone=f"84000{len(suffix):04d}",
            idade=31,
            cidade="Maputo",
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            aceita_verificacao=True,
            foto_perfil=image_file(f"{suffix}-perfil.jpg"),
            bi_frente=image_file(f"{suffix}-bi-frente.jpg"),
            bi_verso=image_file(f"{suffix}-bi-verso.jpg"),
            selfie_com_bi=image_file(f"{suffix}-selfie.jpg"),
            status="APROVADO",
        )
        QuestionarioEntrada.objects.create(
            pedido=pedido,
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
        perfil = PerfilNKATA.objects.create(
            pedido=pedido,
            usuario=user,
            nome_publico=name,
            cidade="Maputo",
            idade=31,
            genero="FEMININO",
            objetivo="RELACIONAMENTO_SERIO",
            sobre_si="Procuro uma relação séria construída com respeito.",
            o_que_valoriza="Respeito, diálogo e compromisso.",
            o_que_nao_aceita="Mentiras e desrespeito.",
            status="ATIVO",
            visivel=True,
        )
        return user, perfil

    def _create_post(self, media_type, media, *, visibility, status="APROVADO"):
        return PublicacaoNKATA.objects.create(
            perfil=self.owner_profile,
            usuario=self.owner,
            media=media,
            tipo_media=media_type,
            legenda="Um pouco de mim.",
            visibilidade=visibility,
            moderacao_status=status,
        )

    def tearDown(self):
        for publication in PublicacaoNKATA.objects.all():
            if publication.media:
                publication.media.delete(save=False)
        for pedido in PedidoEntrada.objects.all():
            for field_name in ("foto_perfil", "bi_frente", "bi_verso", "selfie_com_bi"):
                field = getattr(pedido, field_name)
                if field:
                    field.delete(save=False)

    def test_own_gallery_contains_only_approved_publications(self):
        self.client.force_login(self.owner)

        response = self.client.get("/api/minha-conta/galeria/")

        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()["results"]}
        self.assertEqual(
            ids,
            {self.cover_post.id, self.matches_post.id, self.video_post.id},
        )
        self.assertNotIn(self.pending_post.id, ids)

    def test_cover_requires_approved_public_image_visible_to_all(self):
        self.client.force_login(self.owner)

        for invalid_id in (self.video_post.id, self.matches_post.id, self.pending_post.id):
            response = self.client.patch(
                "/api/minha-conta/capa/",
                {"publication_id": invalid_id},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)

        response = self.client.patch(
            "/api/minha-conta/capa/",
            {"publication_id": self.cover_post.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.json())
        self.owner_profile.refresh_from_db()
        self.assertEqual(self.owner_profile.capa_publicacao_id, self.cover_post.id)

        remove = self.client.patch(
            "/api/minha-conta/capa/",
            {"publication_id": None},
            content_type="application/json",
        )
        self.assertEqual(remove.status_code, 200)
        self.owner_profile.refresh_from_db()
        self.assertIsNone(self.owner_profile.capa_publicacao_id)

    def test_profile_gallery_respects_publication_visibility(self):
        PerfilNKATA.objects.filter(pk=self.owner_profile.pk).update(
            capa_publicacao_id=self.cover_post.id,
        )
        self.client.force_login(self.viewer)

        response = self.client.get(f"/api/perfis/{self.owner_profile.id}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = {item["id"] for item in payload["gallery"]}
        self.assertIn(self.cover_post.id, ids)
        self.assertIn(self.video_post.id, ids)
        self.assertNotIn(self.matches_post.id, ids)
        self.assertEqual(
            payload["cover_url"],
            f"/api/publicacoes/{self.cover_post.id}/media/",
        )

        MatchPerfil.objects.create(
            perfil_1=self.owner_profile,
            perfil_2=self.viewer_profile,
            status="ATIVO",
        )
        matched = self.client.get(f"/api/perfis/{self.owner_profile.id}/")
        matched_ids = {item["id"] for item in matched.json()["gallery"]}
        self.assertIn(self.matches_post.id, matched_ids)

    def test_deleting_cover_publication_clears_profile_cover(self):
        PerfilNKATA.objects.filter(pk=self.owner_profile.pk).update(
            capa_publicacao_id=self.cover_post.id,
        )
        self.client.force_login(self.owner)

        response = self.client.delete(f"/api/publicacoes/{self.cover_post.id}/")

        self.assertEqual(response.status_code, 200)
        self.owner_profile.refresh_from_db()
        self.assertIsNone(self.owner_profile.capa_publicacao_id)
