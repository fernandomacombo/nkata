from django.test import SimpleTestCase
from django.urls import resolve

from .plan_service import PLAN_DEFINITIONS
from .posts_api import POST_CAPTIONS
from .posts_models import PublicacaoNKATA, ReacaoPublicacaoNKATA


class PublicationRulesTests(SimpleTestCase):
    def test_publicar_media_exige_plano_pago(self):
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["feed_media_publish"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["feed_media_publish"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["feed_media_publish"])

    def test_feed_continua_visivel_no_plano_livre(self):
        self.assertTrue(PLAN_DEFINITIONS["LIVRE"]["features"]["feed_view"])

    def test_legendas_sao_predefinidas(self):
        values = {item["value"] for item in POST_CAPTIONS}
        self.assertIn("SEM_LEGENDA", values)
        self.assertTrue(all("text" in item for item in POST_CAPTIONS))

    def test_rotas_de_publicacoes_resolvem(self):
        self.assertEqual(resolve("/api/publicacoes/").url_name, "publicacoes")
        self.assertEqual(
            resolve("/api/publicacoes/9/reacoes/").url_name,
            "reacoes_publicacao",
        )

    def test_modelos_nao_criam_comentarios(self):
        field_names = {field.name for field in PublicacaoNKATA._meta.get_fields()}
        self.assertNotIn("comentarios", field_names)
        self.assertEqual(
            ReacaoPublicacaoNKATA._meta.db_table,
            "entradas_reacaopublicacaonkata",
        )


from uuid import uuid4
from django.test import TestCase, override_settings
from .test_conversations import profile
from .test_profile_gallery_api import image_file, video_file
from .models import EnvioPublicacaoCreditoNKATA, MovimentoCreditoNKATA
from .wallet_service import credit_balance, record_movement


@override_settings(NKATA_CREDIT_ONLY_ENABLED=True, NKATA_CREDIT_TRANSITION_ENABLED=True,
                   NKATA_CREDIT_SPENDING_ENABLED=True)
class CreditPublicationTests(TestCase):
    def setUp(self):
        self.member = profile(76)
        self.user = self.member.usuario
        self.client.force_login(self.user)
        self.url = "/api/publicacoes/"

    def submit(self, cost, key=None, video=False):
        return self.client.post(self.url, {"media": video_file() if video else image_file(),
            "key": str(key or uuid4()), "expected_cost": str(cost),
            "legenda": "SEM_LEGENDA", "visibilidade": "TODOS"})

    def fund(self):
        record_movement(self.user, key="post-test", kind="AJUSTE", amount=10,
                        reference="TEST", reason="Saldo de teste")

    def test_free_daily_photo_and_no_reset_after_deletion(self):
        key = uuid4()
        result = self.submit(0, key)
        self.assertEqual(result.status_code, 202, result.content)
        self.assertEqual(self.submit(0, key).status_code, 200)
        self.assertEqual(EnvioPublicacaoCreditoNKATA.objects.count(), 1)
        self.assertEqual(credit_balance(self.user), 0)
        pk = result.json()["publication"]["id"]
        self.assertEqual(self.client.delete(f"{self.url}{pk}/").status_code, 200)
        self.assertEqual(self.submit(0, key).status_code, 409)
        self.assertEqual(self.submit(0).status_code, 409)
        self.assertEqual(self.submit(2).status_code, 409)
        self.assertEqual(EnvioPublicacaoCreditoNKATA.objects.count(), 1)

    def test_paid_photos_and_videos_are_charged_once(self):
        self.fund()
        self.assertEqual(self.submit(0).status_code, 202)
        key = uuid4()
        result = self.submit(2, key)
        self.assertEqual(result.status_code, 202, result.content)
        self.assertEqual(self.submit(2, key).status_code, 200)
        self.assertEqual(self.submit(5, key, video=True).status_code, 409)
        self.assertEqual(self.submit(5, video=True).status_code, 202)
        self.assertEqual(credit_balance(self.user), 3)
        self.assertEqual(MovimentoCreditoNKATA.objects.filter(tipo="CONSUMO").count(), 2)
        self.assertEqual(EnvioPublicacaoCreditoNKATA.objects.count(), 3)
        self.assertEqual(PublicacaoNKATA.objects.filter(usuario=self.user, moderacao_status="PENDENTE").count(), 3)

    def test_unverified_member_can_view_but_not_publish(self):
        self.member.pedido.identidade_revogada = True
        self.member.pedido.save()
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertFalse(self.client.get(self.url).json()["capabilities"]["publish_media_enabled"])
        self.assertEqual(self.submit(0).status_code, 403)
        self.assertFalse(EnvioPublicacaoCreditoNKATA.objects.exists())
