"""Local contact checks for profile photos. Identity evidence stays outside this flow."""
import logging
import shutil
import subprocess

from .media_inspection_service import contact_signals_from_text, scan_qr_codes

logger = logging.getLogger(__name__)
CONTACT_WARNING = "Envie uma fotografia sem telefone, WhatsApp, email, redes sociais, links ou códigos QR."


def profile_photo_has_contact(data):
    signals, _ = scan_qr_codes([data])
    if any(signals.values()):
        return True

    executable = shutil.which("tesseract")
    if not executable:
        return False
    try:
        result = subprocess.run(
            [executable, "stdin", "stdout", "--psm", "11"],
            input=data, capture_output=True, timeout=4, check=True,
            env={"OMP_THREAD_LIMIT": "1"},
        )
    except (OSError, subprocess.SubprocessError):
        logger.warning("Leitura automática de contactos indisponível para uma fotografia.")
        return False
    return any(contact_signals_from_text(result.stdout.decode(errors="replace")).values())
