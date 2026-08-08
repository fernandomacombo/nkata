import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from . import moments_api, posts_api
from .content_moderation_queue import (
    QUEUE_PROVIDER,
    process_claimed_analysis,
    queue_content_media_analysis,
)


class MediaModerationQueueTests(SimpleTestCase):
    @patch("entradas.content_moderation_queue.AnaliseAutomaticaConteudoNKATA.objects.update_or_create")
    def test_queue_cria_registo_leve_sem_analisar_ficheiro(self, update_or_create):
        queued = queue_content_media_analysis(
            content_type="PUBLICACAO",
            content_id=41,
            media_type="IMAGEM",
        )

        self.assertTrue(queued)
        _, kwargs = update_or_create.call_args
        self.assertEqual(kwargs["content_type"], "PUBLICACAO")
        self.assertEqual(kwargs["content_id"], 41)
        self.assertEqual(kwargs["defaults"]["provider"], QUEUE_PROVIDER)
        self.assertEqual(kwargs["defaults"]["risk_level"], "INDEFINIDO")
        self.assertEqual(kwargs["defaults"]["status"], "REVISAO")

    def test_queue_rejeita_tipo_de_media_invalido(self):
        self.assertFalse(queue_content_media_analysis(
            content_type="MOMENTO",
            content_id=8,
            media_type="TEXTO",
        ))

    def test_endpoints_de_upload_enfileiram_em_vez_de_analisar_sincronamente(self):
        posts_source = inspect.getsource(posts_api.api_publicacoes)
        moments_source = inspect.getsource(moments_api.api_momentos)

        self.assertIn("queue_content_media_analysis", posts_source)
        self.assertNotIn("analyse_content_media", posts_source)
        self.assertIn("queue_content_media_analysis", moments_source)
        self.assertNotIn("analyse_content_media", moments_source)

    @patch("entradas.content_moderation_queue.analyse_content_media")
    @patch("entradas.content_moderation_queue._pending_content_for")
    def test_worker_e_que_executa_motor_real(self, pending_content_for, analyse):
        content = SimpleNamespace(
            media=MagicMock(),
            tipo_media="VIDEO",
        )
        analysis = SimpleNamespace(
            id=7,
            content_type="MOMENTO",
            content_id=19,
            media_type="VIDEO",
        )
        pending_content_for.return_value = content
        analyse.return_value = SimpleNamespace(id=7)

        self.assertTrue(process_claimed_analysis(analysis))
        analyse.assert_called_once_with(
            content_type="MOMENTO",
            content_id=19,
            file_field=content.media,
            media_type="VIDEO",
        )

    @patch("entradas.content_moderation_queue._mark_skipped")
    @patch("entradas.content_moderation_queue._pending_content_for", return_value=None)
    def test_conteudo_ja_decidido_nao_e_processado_novamente(
        self,
        pending_content_for,
        mark_skipped,
    ):
        analysis = SimpleNamespace(
            id=9,
            content_type="PUBLICACAO",
            content_id=22,
            media_type="IMAGEM",
        )

        self.assertTrue(process_claimed_analysis(analysis))
        pending_content_for.assert_called_once_with(analysis)
        mark_skipped.assert_called_once()
