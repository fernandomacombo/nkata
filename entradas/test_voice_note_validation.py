from io import BytesIO
from unittest.mock import patch
import wave
import subprocess
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from types import SimpleNamespace

from .audio_validation import prepare_voice_note, InvalidVoiceNote, AudioDecoderUnavailable
from .chat_media_api import api_audios_match


def wav_note(seconds=1):
    buffer = BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * (8000 * seconds))
    return SimpleUploadedFile("voice.wav", buffer.getvalue(), content_type="audio/wav")


class VoiceNoteValidationTests(SimpleTestCase):
    def test_browser_webm_mp4_and_ogg_are_decoded(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.wav"
            source.write_bytes(wav_note(2).read())
            for extension, codec in (("webm", "libopus"), ("m4a", "aac"), ("ogg", "libopus")):
                with self.subTest(extension=extension):
                    target = Path(folder) / f"voice.{extension}"
                    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(source), "-c:a", codec, str(target)],
                        check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    prepared, duration = prepare_voice_note(SimpleUploadedFile(target.name, target.read_bytes()))
                    self.assertGreaterEqual(duration, 2)
                    self.assertLessEqual(duration, 3)
                    self.assertGreater(prepared.size, 100)

    def test_real_audio_is_decoded_and_duration_is_measured(self):
        prepared, duration = prepare_voice_note(wav_note(2))
        self.assertEqual(duration, 2)
        self.assertEqual(prepared.name, "nota-de-voz.wav")
        with wave.open(prepared, "rb") as audio:
            self.assertEqual(audio.getframerate(), 16000)
            self.assertEqual(audio.getnchannels(), 1)

    def test_fake_webm_is_rejected_even_with_audio_mime(self):
        upload = SimpleUploadedFile("voice.webm", b"not audio", content_type="audio/webm")
        with self.assertRaises(InvalidVoiceNote):
            prepare_voice_note(upload)

    def test_real_duration_over_limit_is_rejected(self):
        with self.assertRaises(InvalidVoiceNote):
            prepare_voice_note(wav_note(181))

    def test_missing_decoder_fails_closed(self):
        with patch("entradas.audio_validation.subprocess.run", side_effect=FileNotFoundError), self.assertRaises(AudioDecoderUnavailable):
            prepare_voice_note(wav_note())

    def test_non_finite_declared_duration_returns_validation_error(self):
        for value in ("Infinity", "-Infinity", "NaN", "1e999", "invalid"):
            request = APIRequestFactory().post("/api/", {"duracao_segundos":value}, format="json")
            force_authenticate(request, user=SimpleNamespace(is_authenticated=True, pk=1))
            with patch("entradas.chat_media_api._match_do_utilizador", return_value=object()), patch("entradas.chat_media_api.chat_capabilities", return_value={"audio_enabled":True}):
                response = api_audios_match(request, 1)
            self.assertEqual(response.status_code, 400)

    def test_endpoint_rejects_fake_audio_before_storage(self):
        request = APIRequestFactory().post("/api/", {
            "audio":SimpleUploadedFile("voice.webm", b"not audio", content_type="audio/webm"),
            "duracao_segundos":"10",
        }, format="multipart")
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True, pk=1))
        with patch("entradas.chat_media_api._match_do_utilizador", return_value=object()), patch("entradas.chat_media_api.chat_capabilities", return_value={"audio_enabled":True}), patch("entradas.chat_media_api.MensagemAudioMatchNKATA.objects.create") as save:
            response = api_audios_match(request, 1)
        self.assertEqual(response.status_code, 400)
        save.assert_not_called()
