from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse

from .chat_media_api import _validate_audio
from .chat_media_models import MensagemAudioMatchNKATA
from .plan_service import PLAN_DEFINITIONS


class ChatAudioRulesTests(SimpleTestCase):
    def test_modelo_audio_permanece_isolado_de_migrations(self):
        self.assertFalse(MensagemAudioMatchNKATA._meta.managed)
        self.assertEqual(
            MensagemAudioMatchNKATA._meta.db_table,
            "entradas_mensagemaudiomatchnkata",
        )

    def test_audio_so_esta_ativo_em_planos_pagos(self):
        self.assertFalse(PLAN_DEFINITIONS["LIVRE"]["features"]["chat_audio"])
        self.assertTrue(PLAN_DEFINITIONS["ESSENCIAL"]["features"]["chat_audio"])
        self.assertTrue(PLAN_DEFINITIONS["PREMIUM"]["features"]["chat_audio"])

    def test_rotas_de_audio_sao_proprias_do_match(self):
        self.assertEqual(
            reverse("entradas_api:audios_match", kwargs={"match_id": 7}),
            "/api/minha-conta/matches/7/audio/",
        )
        self.assertEqual(
            reverse(
                "entradas_api:media_audio_match",
                kwargs={"match_id": 7, "audio_id": 12},
            ),
            "/api/minha-conta/matches/7/audio/12/media/",
        )

    def test_mime_webm_com_codec_do_chrome_e_aceite(self):
        audio = SimpleUploadedFile(
            "nota-voz.webm",
            b"fake-audio-content",
            content_type="audio/webm;codecs=opus",
        )
        self.assertIsNone(_validate_audio(audio, 18))

    def test_duracao_acima_de_tres_minutos_e_rejeitada(self):
        audio = SimpleUploadedFile(
            "nota-voz.m4a",
            b"fake-audio-content",
            content_type="audio/mp4",
        )
        error = _validate_audio(audio, 181)
        self.assertIn("180", error)
