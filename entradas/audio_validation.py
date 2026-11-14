"""Decode untrusted voice notes locally and retain only canonical audio."""
import math
import subprocess
import tempfile
import wave
from pathlib import Path

from django.core.files.base import ContentFile


class InvalidVoiceNote(ValueError):
    pass


class AudioDecoderUnavailable(RuntimeError):
    pass


def prepare_voice_note(upload, max_seconds=180):
    with tempfile.TemporaryDirectory(prefix="nkata-audio-") as folder:
        source = Path(folder) / "input"
        output = Path(folder) / "voice.wav"
        try:
            upload.seek(0)
            with source.open("wb") as handle:
                for chunk in upload.chunks():
                    handle.write(chunk)
            command = [
                "ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror",
                "-protocol_whitelist", "file,pipe",
                "-format_whitelist", "matroska,webm,mov,mp4,m4a,3gp,3g2,mj2,ogg,mp3,wav",
                "-i", str(source), "-map", "0:a:0", "-vn",
                "-t", str(max_seconds + 1), "-ac", "1", "-ar", "16000",
                "-threads", "1", "-c:a", "pcm_s16le", "-f", "wav", str(output),
            ]
            result = subprocess.run(command, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=20, check=False)
            if result.returncode or not output.is_file():
                raise InvalidVoiceNote("A nota de voz não contém áudio válido. Grave novamente.")
            with wave.open(str(output), "rb") as audio:
                seconds = audio.getnframes() / audio.getframerate()
            if not 0 < seconds <= max_seconds:
                raise InvalidVoiceNote(f"A nota de voz deve ter no máximo {max_seconds} segundos.")
            return ContentFile(output.read_bytes(), name="nota-de-voz.wav"), max(1, math.ceil(seconds))
        except FileNotFoundError:
            raise AudioDecoderUnavailable("A gravação de voz está temporariamente indisponível.") from None
        except (subprocess.TimeoutExpired, wave.Error, EOFError):
            raise InvalidVoiceNote("Não foi possível validar a nota de voz. Grave novamente.") from None
        finally:
            upload.seek(0)
