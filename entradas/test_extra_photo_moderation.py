from io import BytesIO
from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from .models import PedidoEntrada, PerfilNKATA
from .user_roles import set_admin_capabilities


def valid_photo(name):
    stream = BytesIO()
    Image.new("RGB", (600, 600), "maroon").save(stream, format="JPEG")
    return SimpleUploadedFile(name, stream.getvalue(), content_type="image/jpeg")


class ExtraPhotoModerationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="photo_owner", password="safe-password", email="owner@example.org")
        self.viewer = User.objects.create_user(username="photo_viewer", password="safe-password", email="viewer@example.org")
        self.moderator = User.objects.create_user(username="photo_moderator", password="safe-password", email="moderator@example.org", is_staff=True)
        self.unauthorized = User.objects.create_user(username="photo_staff", password="safe-password", email="staff@example.org", is_staff=True)
        set_admin_capabilities(self.moderator, ["content"])
        self.pedido = PedidoEntrada.objects.create(
            nome_completo="Pessoa Exemplo", email="owner@example.org", telefone="840000234",
            idade=29, cidade="Maputo", genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
            foto_perfil=valid_photo("principal.jpg"),
            foto_extra_1=valid_photo("segunda.jpg"),
            status="APROVADO",
        )
        self.profile = PerfilNKATA.objects.create(
            pedido=self.pedido, usuario=self.owner, nome_publico="Exemplo", cidade="Maputo",
            idade=29, genero="FEMININO", objetivo="RELACIONAMENTO_SERIO",
            status="ATIVO", visivel=True,
        )

    def tearDown(self):
        self.pedido.refresh_from_db()
        for field_name in ("foto_perfil", "foto_extra_1", "foto_extra_2", "foto_extra_3"):
            photo = getattr(self.pedido, field_name)
            if photo:
                photo.delete(save=False)

    def url(self, slot=1):
        return f"/api/perfis/{self.profile.pk}/fotografias/{slot}/"

    def moderation_url(self, slot=1):
        return f"/api/painel/fotografias/{self.profile.pk}/{slot}/rever/"

    def test_pending_photo_private_and_non_moderator_blocked(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        response.close()
        result = self.client.patch(
            "/api/minha-conta/fotografias/1/", '{"visible": true}',
            content_type="application/json",
        )
        self.assertEqual(result.status_code, 400)
        self.client.force_login(self.unauthorized)
        self.assertEqual(self.client.get("/api/painel/fotografias/").status_code, 403)

    def test_moderator_approval_requires_reviewed_version(self):
        self.client.force_login(self.moderator)
        response = self.client.get("/api/painel/fotografias/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(1, [row["slot"] for row in response.json()["results"]], {"payload": response.json(), "profile_status": self.profile.status})
        item = next(row for row in response.json()["results"] if row["slot"] == 1)
        stale = self.client.post(self.moderation_url(), '{"action": "approve", "version": "old"}', content_type="application/json")
        self.assertEqual(stale.status_code, 409)
        approved = self.client.post(self.moderation_url(), '{"action": "approve", "version": "' + item["version"] + '"}', content_type="application/json")
        self.assertEqual(approved.status_code, 200)
        self.client.force_login(self.owner)
        # Photo approval never overrides a paused account. Simulate an active
        # member explicitly before testing their voluntary visibility choice.
        self.profile.refresh_from_db()
        if self.profile.status == "PAUSADO":
            denied = self.client.patch(
                "/api/minha-conta/fotografias/1/", '{"visible": true}',
                content_type="application/json",
            )
            self.assertEqual(denied.status_code, 400)
        PerfilNKATA.objects.filter(pk=self.profile.pk).update(status="ATIVO", visivel=True)
        visible = self.client.patch(
            "/api/minha-conta/fotografias/1/", '{"visible": true}',
            content_type="application/json",
        )
        self.assertEqual(visible.status_code, 200)
        self.client.force_login(self.viewer)
        photo = self.client.get(self.url())
        self.assertEqual(photo.status_code, 200)
        photo.close()

    def test_rejection_hides_photo_and_owner_can_delete(self):
        self.client.force_login(self.moderator)
        pending = self.client.get("/api/painel/fotografias/")
        self.assertIn(1, [row["slot"] for row in pending.json()["results"]], {"payload": pending.json()})
        item = next(row for row in pending.json()["results"] if row["slot"] == 1)
        self.client.post(self.moderation_url(), '{"action": "approve", "version": "' + item["version"] + '"}', content_type="application/json")
        self.pedido.refresh_from_db()
        self.pedido.foto_extra_1_visivel = True
        self.pedido.save(update_fields=["foto_extra_1_visivel"])
        item = next(row for row in self.client.get("/api/painel/fotografias/?status=APROVADO").json()["results"] if row["slot"] == 1)
        response = self.client.post(self.moderation_url(), '{"action": "reject", "version": "' + item["version"] + '"}', content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.pedido.refresh_from_db()
        self.assertFalse(self.pedido.foto_extra_1_visivel)
        self.client.force_login(self.owner)
        response = self.client.delete("/api/minha-conta/fotografias/1/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["results"][0]["exists"])
