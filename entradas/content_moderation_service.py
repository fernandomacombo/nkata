import base64
import hashlib
import io
import json
import mimetypes
import os
from urllib import error as urlerror
from urllib import request as urlrequest

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.db import DatabaseError

from .content_moderation_models import AnaliseAutomaticaConteudoNKATA


OPENAI_MODERATION_URL = "https://api.openai.com/v1/moderations"


def risk_from_moderation_result(result):
    categories = result.get("categories") or {}
    flagged = bool(result.get("flagged"))

    if categories.get("sexual/minors"):
        return "CRITICO"
    if categories.get("sexual") or categories.get("violence/graphic"):
        return "ALTO"
    if flagged or any(bool(value) for value in categories.values()):
        return "MEDIO"
    return "BAIXO"


def status_from_risk(risk_level):
    if risk_level == "BAIXO":
        return "BAIXO_RISCO"
    if risk_level in {"ALTO", "CRITICO"}:
        return "ALTO_RISCO"
    return "REVISAO"


def _hash_file(file_field):
    digest = hashlib.sha256()
    file_field.open("rb")
    try:
        while True:
            chunk = file_field.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        file_field.close()
    return digest.hexdigest()


def _image_metadata(file_field):
    file_field.open("rb")
    try:
        image = Image.open(file_field)
        width, height = image.size
        return int(width), int(height)
    except (UnidentifiedImageError, OSError, ValueError):
        return None, None
    finally:
        file_field.close()


def _moderation_image_data_url(file_field):
    """Cria uma cópia reduzida apenas para classificação automática."""
    file_field.open("rb")
    try:
        image = Image.open(file_field)
        image.thumbnail((1600, 1600))

        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, "white")
            alpha = image.getchannel("A")
            background.paste(image.convert("RGB"), mask=alpha)
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=82, optimize=True)
    finally:
        file_field.close()

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _openai_moderate_image(file_field):
    api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    model = str(
        getattr(settings, "NKATA_OPENAI_MODERATION_MODEL", "omni-moderation-latest")
        or "omni-moderation-latest"
    ).strip()
    timeout = int(getattr(settings, "NKATA_MEDIA_MODERATION_TIMEOUT", 15))

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não está configurada.")

    payload = {
        "model": model,
        "input": [
            {
                "type": "image_url",
                "image_url": {"url": _moderation_image_data_url(file_field)},
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        OPENAI_MODERATION_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urlerror.HTTPError, urlerror.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Falha no serviço automático de moderação: {exc}") from exc

    results = data.get("results") or []
    if not results:
        raise RuntimeError("O serviço de moderação não devolveu um resultado utilizável.")

    result = results[0]
    return {
        "model": data.get("model") or model,
        "flagged": bool(result.get("flagged")),
        "categories": result.get("categories") or {},
        "category_scores": result.get("category_scores") or {},
    }


def _duplicate_grave_exists(file_sha256, *, content_type, content_id):
    if not file_sha256:
        return False
    try:
        return AnaliseAutomaticaConteudoNKATA.objects.filter(
            file_sha256=file_sha256,
            human_decision="GRAVE",
        ).exclude(
            content_type=content_type,
            content_id=content_id,
        ).exists()
    except DatabaseError:
        return False


def analyse_content_media(*, content_type, content_id, file_field, media_type):
    if not file_field or not content_id:
        return None

    content_type = str(content_type or "").strip().upper()
    media_type = str(media_type or "").strip().upper()
    provider = str(
        getattr(settings, "NKATA_MEDIA_MODERATION_PROVIDER", "manual") or "manual"
    ).strip().lower()

    file_sha256 = ""
    width = None
    height = None
    media_bytes = 0
    categories = {}
    category_scores = {}
    model_name = ""
    flagged = False
    risk_level = "INDEFINIDO"
    status = "REVISAO"
    notes = "Revisão humana obrigatória antes da publicação."

    try:
        media_bytes = int(file_field.size or 0)
    except (OSError, ValueError, AttributeError):
        media_bytes = 0

    try:
        file_sha256 = _hash_file(file_field)
    except (OSError, ValueError):
        notes = "Não foi possível calcular a impressão digital do ficheiro. Revisão humana obrigatória."

    if media_type == "IMAGEM":
        width, height = _image_metadata(file_field)

    if _duplicate_grave_exists(
        file_sha256,
        content_type=content_type,
        content_id=content_id,
    ):
        flagged = True
        risk_level = "CRITICO"
        status = "ALTO_RISCO"
        categories = {"duplicate_previously_rejected_severe_media": True}
        notes = (
            "Ficheiro idêntico a conteúdo anteriormente rejeitado por violação grave. "
            "Não aprovar sem revisão da equipa."
        )
    elif media_type == "VIDEO":
        provider = "manual"
        notes = (
            "Vídeo recebido. A análise automática de frames ainda não está configurada; "
            "revisão humana obrigatória."
        )
    elif provider == "openai" and media_type == "IMAGEM":
        try:
            result = _openai_moderate_image(file_field)
            model_name = result["model"]
            flagged = result["flagged"]
            categories = result["categories"]
            category_scores = result["category_scores"]
            risk_level = risk_from_moderation_result(result)
            status = status_from_risk(risk_level)
            notes = (
                "Pré-moderação automática concluída. "
                "A decisão final continua dependente da revisão humana."
            )
        except RuntimeError as exc:
            status = "ERRO"
            risk_level = "INDEFINIDO"
            notes = f"{exc} O conteúdo permanece pendente para revisão humana."
    else:
        provider = "manual"
        notes = (
            "Motor automático de imagem não configurado. "
            "O conteúdo permanece pendente para revisão humana."
        )

    defaults = {
        "media_type": media_type,
        "provider": provider,
        "model_name": model_name,
        "status": status,
        "risk_level": risk_level,
        "flagged": flagged,
        "file_sha256": file_sha256,
        "media_bytes": media_bytes,
        "image_width": width,
        "image_height": height,
        "categories": categories,
        "category_scores": category_scores,
        "notes": notes[:500],
    }

    try:
        analysis, _ = AnaliseAutomaticaConteudoNKATA.objects.update_or_create(
            content_type=content_type,
            content_id=content_id,
            defaults=defaults,
        )
        return analysis
    except DatabaseError:
        # Fail closed: o conteúdo original continua PENDENTE mesmo se a tabela
        # de apoio ainda não tiver sido preparada neste ambiente.
        return None


def analysis_for(content_type, content_id):
    if not content_id:
        return None
    try:
        return AnaliseAutomaticaConteudoNKATA.objects.filter(
            content_type=str(content_type).upper(),
            content_id=content_id,
        ).first()
    except DatabaseError:
        return None


def record_human_decision(content_type, content_id, decision):
    decision = str(decision or "").strip().upper()
    if decision not in {"APROVADO", "REJEITADO", "GRAVE"}:
        return False
    try:
        updated = AnaliseAutomaticaConteudoNKATA.objects.filter(
            content_type=str(content_type).upper(),
            content_id=content_id,
        ).update(human_decision=decision)
        return bool(updated)
    except DatabaseError:
        return False


def moderation_provider_label():
    provider = str(
        getattr(settings, "NKATA_MEDIA_MODERATION_PROVIDER", "manual") or "manual"
    ).strip().lower()
    if provider == "openai":
        return "OpenAI Moderation (imagem)"
    return "Revisão humana / sem motor externo"
