import base64
import io
import json
import re
import tempfile
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

import cv2
import numpy as np
from PIL import Image
from django.conf import settings


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
MAX_VIDEO_FRAMES = 6

PHONE_RE = re.compile(r"(?<!\d)(?:\+?258[\s.-]?)?(?:8[2-7])(?:[\s.-]?\d){7}(?!\d)")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
URL_RE = re.compile(r"(?:https?://|www\.)[^\s]+", re.IGNORECASE)
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Z0-9_.]{3,32}", re.IGNORECASE)


def _read_file_bytes(file_field):
    file_field.open("rb")
    try:
        return file_field.read()
    finally:
        file_field.close()


def _jpeg_data_url_from_bytes(data, max_side=1600):
    image = Image.open(io.BytesIO(data))
    image.thumbnail((max_side, max_side))
    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", image.size, "white")
        alpha = image.getchannel("A")
        background.paste(image.convert("RGB"), mask=alpha)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=82, optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def image_bytes_from_file(file_field):
    return _read_file_bytes(file_field)


def extract_video_frames(file_field, max_frames=MAX_VIDEO_FRAMES):
    """Extrai frames distribuídos pelo vídeo. Retorna JPEG bytes."""
    data = _read_file_bytes(file_field)
    suffix = Path(getattr(file_field, "name", "video.mp4")).suffix or ".mp4"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as temporary:
        temporary.write(data)
        temporary.flush()

        capture = cv2.VideoCapture(temporary.name)
        if not capture.isOpened():
            capture.release()
            return []

        try:
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if frame_count <= 0:
                indexes = list(range(max_frames))
            elif frame_count <= max_frames:
                indexes = list(range(frame_count))
            else:
                indexes = sorted({
                    int(round(value))
                    for value in np.linspace(0, frame_count - 1, num=max_frames)
                })

            frames = []
            for index in indexes:
                if frame_count > 0:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue

                height, width = frame.shape[:2]
                longest = max(width, height)
                if longest > 1600:
                    scale = 1600 / longest
                    frame = cv2.resize(
                        frame,
                        (max(1, int(width * scale)), max(1, int(height * scale))),
                        interpolation=cv2.INTER_AREA,
                    )

                encoded_ok, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 82],
                )
                if encoded_ok:
                    frames.append(encoded.tobytes())
            return frames
        finally:
            capture.release()


def _qr_payloads_from_bytes(data):
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        return []

    detector = cv2.QRCodeDetector()
    payloads = []
    try:
        ok, decoded_info, _, _ = detector.detectAndDecodeMulti(image)
        if ok:
            payloads.extend(item.strip() for item in decoded_info if item and item.strip())
    except (cv2.error, ValueError):
        pass

    if not payloads:
        try:
            decoded, _, _ = detector.detectAndDecode(image)
            if decoded and decoded.strip():
                payloads.append(decoded.strip())
        except (cv2.error, ValueError):
            pass
    return list(dict.fromkeys(payloads))


def contact_signals_from_text(text):
    text = str(text or "")
    lowered = text.lower()
    return {
        "contact_phone": bool(PHONE_RE.search(text) or "wa.me/" in lowered or "whatsapp" in lowered),
        "contact_email": bool(EMAIL_RE.search(text) or lowered.startswith("mailto:")),
        "contact_url": bool(URL_RE.search(text)),
        "contact_username": bool(HANDLE_RE.search(text)),
    }


def scan_qr_codes(image_payloads):
    payloads = []
    for data in image_payloads:
        payloads.extend(_qr_payloads_from_bytes(data))
    payloads = list(dict.fromkeys(payloads))

    signals = {
        "qr_code": bool(payloads),
        "contact_phone": False,
        "contact_email": False,
        "contact_url": False,
        "contact_username": False,
    }
    for payload in payloads:
        detected = contact_signals_from_text(payload)
        for key, value in detected.items():
            signals[key] = signals[key] or value

    return signals, payloads[:5]


def _extract_response_text(payload):
    for item in payload.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    return ""


def vision_scan(image_payloads):
    """Procura contactos e sinais comerciais/sexuais visíveis. Opcional."""
    enabled = bool(getattr(settings, "NKATA_MEDIA_VISION_SCAN_ENABLED", False))
    api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    if not enabled or not api_key or not image_payloads:
        return None

    model = str(
        getattr(settings, "NKATA_MEDIA_VISION_MODEL", "gpt-5.6-luna")
        or "gpt-5.6-luna"
    ).strip()
    timeout = int(getattr(settings, "NKATA_MEDIA_MODERATION_TIMEOUT", 20))
    max_images = max(1, min(6, int(getattr(settings, "NKATA_MEDIA_VISION_MAX_IMAGES", 4))))

    content = [{
        "type": "input_text",
        "text": (
            "Analise estas imagens exclusivamente para segurança de uma plataforma de relacionamentos. "
            "Indique se existe texto ou elemento visual mostrando telefone/WhatsApp, email, @username, "
            "URL/link, QR code, publicidade/venda, ou oferta/solicitação de serviços sexuais/prostituição. "
            "Não identifique pessoas. Não faça inferências sobre profissão, identidade ou intenção além do que "
            "estiver explicitamente visível."
        ),
    }]
    for data in image_payloads[:max_images]:
        content.append({
            "type": "input_image",
            "image_url": _jpeg_data_url_from_bytes(data),
            "detail": "high",
        })

    schema = {
        "type": "object",
        "properties": {
            "contact_phone": {"type": "boolean"},
            "contact_email": {"type": "boolean"},
            "contact_username": {"type": "boolean"},
            "contact_url": {"type": "boolean"},
            "qr_code": {"type": "boolean"},
            "advertising_or_sales": {"type": "boolean"},
            "sexual_services_solicitation": {"type": "boolean"},
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 8,
            },
        },
        "required": [
            "contact_phone", "contact_email", "contact_username", "contact_url",
            "qr_code", "advertising_or_sales", "sexual_services_solicitation", "evidence",
        ],
        "additionalProperties": False,
    }

    body = json.dumps({
        "model": model,
        "input": [{"role": "user", "content": content}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "nkata_media_safety_scan",
                "strict": True,
                "schema": schema,
            },
            "verbosity": "low",
        },
        "max_output_tokens": 500,
    }).encode("utf-8")

    request = urlrequest.Request(
        OPENAI_RESPONSES_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        output_text = _extract_response_text(payload)
        result = json.loads(output_text)
        result["model"] = payload.get("model") or model
        return result
    except (urlerror.HTTPError, urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return {
            "scan_error": True,
            "error": str(exc)[:240],
            "model": model,
        }


def merge_inspection_signals(qr_signals, vision_result):
    merged = dict(qr_signals or {})
    if vision_result and not vision_result.get("scan_error"):
        for key in (
            "contact_phone", "contact_email", "contact_username", "contact_url",
            "qr_code", "advertising_or_sales", "sexual_services_solicitation",
        ):
            merged[key] = bool(merged.get(key) or vision_result.get(key))
    return merged


def risk_from_inspection_signals(signals):
    signals = signals or {}
    if signals.get("sexual_services_solicitation"):
        return "CRITICO"
    if any(signals.get(key) for key in (
        "contact_phone", "contact_email", "contact_username", "contact_url", "qr_code",
    )):
        return "ALTO"
    if signals.get("advertising_or_sales"):
        return "ALTO"
    return "BAIXO"
