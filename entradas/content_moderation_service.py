import base64
import hashlib
import io
import json
from urllib import error as urlerror
from urllib import request as urlrequest

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.db import DatabaseError

from .content_moderation_models import AnaliseAutomaticaConteudoNKATA
from .media_inspection_service import (
    extract_video_frames,
    image_bytes_from_file,
    merge_inspection_signals,
    risk_from_inspection_signals,
    scan_qr_codes,
    vision_scan,
)


OPENAI_MODERATION_URL = "https://api.openai.com/v1/moderations"
RISK_ORDER = {
    "INDEFINIDO": 0,
    "BAIXO": 1,
    "MEDIO": 2,
    "ALTO": 3,
    "CRITICO": 4,
}


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


def highest_risk(*levels):
    valid = [level for level in levels if level in RISK_ORDER]
    if not valid:
        return "INDEFINIDO"
    return max(valid, key=lambda level: RISK_ORDER[level])


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


def _moderation_data_url_from_bytes(data):
    image = Image.open(io.BytesIO(data))
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
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _openai_moderate_image_bytes(data):
    api_key = str(getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    model = str(
        getattr(settings, "NKATA_OPENAI_MODERATION_MODEL", "omni-moderation-latest")
        or "omni-moderation-latest"
    ).strip()
    timeout = int(getattr(settings, "NKATA_MEDIA_MODERATION_TIMEOUT", 20))

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não está configurada.")

    payload = {
        "model": model,
        "input": [
            {
                "type": "image_url",
                "image_url": {"url": _moderation_data_url_from_bytes(data)},
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    request = urlrequest.Request(
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
        with urlrequest.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (urlerror.HTTPError, urlerror.URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Falha no serviço automático de moderação: {exc}") from exc

    results = response_data.get("results") or []
    if not results:
        raise RuntimeError("O serviço de moderação não devolveu um resultado utilizável.")

    result = results[0]
    return {
        "model": response_data.get("model") or model,
        "flagged": bool(result.get("flagged")),
        "categories": result.get("categories") or {},
        "category_scores": result.get("category_scores") or {},
    }


def _merge_moderation_results(results):
    if not results:
        return None

    categories = {}
    category_scores = {}
    flagged = False
    risk = "BAIXO"
    model_names = []

    for result in results:
        flagged = flagged or bool(result.get("flagged"))
        risk = highest_risk(risk, risk_from_moderation_result(result))
        model_name = str(result.get("model") or "").strip()
        if model_name and model_name not in model_names:
            model_names.append(model_name)

        for key, value in (result.get("categories") or {}).items():
            categories[key] = bool(categories.get(key) or value)
        for key, value in (result.get("category_scores") or {}).items():
            try:
                category_scores[key] = max(float(category_scores.get(key, 0)), float(value))
            except (TypeError, ValueError):
                continue

    return {
        "flagged": flagged,
        "risk": risk,
        "categories": categories,
        "category_scores": category_scores,
        "models": model_names,
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


def _image_payloads(file_field, media_type):
    if media_type == "IMAGEM":
        try:
            return [image_bytes_from_file(file_field)], None
        except (OSError, ValueError):
            return [], "Não foi possível preparar a imagem para inspeção automática."

    if media_type == "VIDEO":
        try:
            frames = extract_video_frames(file_field)
        except (OSError, ValueError):
            frames = []
        if not frames:
            return [], "Não foi possível extrair frames do vídeo; revisão humana obrigatória."
        return frames, None

    return [], "Tipo de media não suportado pela inspeção automática."


def analyse_content_media(*, content_type, content_id, file_field, media_type):
    if not file_field or not content_id:
        return None

    content_type = str(content_type or "").strip().upper()
    media_type = str(media_type or "").strip().upper()
    moderation_provider = str(
        getattr(settings, "NKATA_MEDIA_MODERATION_PROVIDER", "manual") or "manual"
    ).strip().lower()

    file_sha256 = ""
    width = None
    height = None
    media_bytes = 0
    categories = {}
    category_scores = {}
    model_names = []
    provider_parts = ["opencv"]
    flagged = False
    risk_level = "INDEFINIDO"
    status = "REVISAO"
    note_parts = ["Revisão humana obrigatória antes da publicação."]

    try:
        media_bytes = int(file_field.size or 0)
    except (OSError, ValueError, AttributeError):
        media_bytes = 0

    try:
        file_sha256 = _hash_file(file_field)
    except (OSError, ValueError):
        note_parts.append("Não foi possível calcular a impressão digital do ficheiro.")

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
        categories = {"nkata/duplicate_severe_media": True}
        note_parts.append(
            "Ficheiro idêntico a conteúdo anteriormente rejeitado por violação grave."
        )
    else:
        image_payloads, payload_error = _image_payloads(file_field, media_type)
        if payload_error:
            note_parts.append(payload_error)
        elif media_type == "VIDEO":
            note_parts.append(f"Foram extraídos {len(image_payloads)} frame(s) distribuídos pelo vídeo.")

        # QR Code é verificado localmente mesmo quando nenhum serviço externo está ativo.
        qr_signals = {}
        qr_payloads = []
        if image_payloads:
            try:
                qr_signals, qr_payloads = scan_qr_codes(image_payloads)
            except (ValueError, RuntimeError):
                qr_signals = {}
                note_parts.append("A leitura local de QR Code não pôde ser concluída.")

        if qr_payloads:
            note_parts.append(
                f"Foram detectados {len(qr_payloads)} QR Code(s). O conteúdo dos códigos não é armazenado."
            )

        # Inspeção visual opcional procura contactos/publicidade e serviços sexuais.
        vision_result = vision_scan(image_payloads) if image_payloads else None
        vision_complete = bool(vision_result and not vision_result.get("scan_error"))
        if vision_complete:
            provider_parts.append("openai-vision")
            vision_model = str(vision_result.get("model") or "").strip()
            if vision_model:
                model_names.append(vision_model)
            note_parts.append("Inspeção visual de contactos e finalidade comercial concluída.")
        elif vision_result and vision_result.get("scan_error"):
            note_parts.append("A inspeção visual externa falhou; o conteúdo permanece pendente.")
        elif not getattr(settings, "NKATA_MEDIA_VISION_SCAN_ENABLED", False):
            note_parts.append("Leitura visual de texto/contactos não está ativada neste ambiente.")

        inspection_signals = merge_inspection_signals(qr_signals, vision_result)
        for key, value in inspection_signals.items():
            categories[f"nkata/{key}"] = bool(value)

        has_inspection_signal = any(bool(value) for value in inspection_signals.values())
        inspection_risk = (
            risk_from_inspection_signals(inspection_signals)
            if has_inspection_signal
            else ("BAIXO" if vision_complete else "INDEFINIDO")
        )

        # Moderação de segurança é executada em cada imagem/frame quando ativada.
        moderation_complete = False
        moderation_results = []
        if moderation_provider == "openai" and image_payloads:
            provider_parts.append("openai-moderation")
            for image_data in image_payloads:
                try:
                    moderation_results.append(_openai_moderate_image_bytes(image_data))
                except RuntimeError as exc:
                    note_parts.append(str(exc))
                    break
            moderation_complete = len(moderation_results) == len(image_payloads)
        elif moderation_provider != "openai":
            note_parts.append("Classificador externo de segurança não está ativado neste ambiente.")

        merged_moderation = _merge_moderation_results(moderation_results)
        moderation_risk = "INDEFINIDO"
        if merged_moderation:
            moderation_risk = merged_moderation["risk"]
            flagged = flagged or merged_moderation["flagged"]
            for key, value in merged_moderation["categories"].items():
                categories[key] = bool(categories.get(key) or value)
            category_scores.update(merged_moderation["category_scores"])
            for model_name in merged_moderation["models"]:
                if model_name not in model_names:
                    model_names.append(model_name)

        # Sinais proibidos prevalecem mesmo quando uma verificação externa falha.
        detected_risk = highest_risk(moderation_risk, inspection_risk)
        if RISK_ORDER.get(detected_risk, 0) >= RISK_ORDER["MEDIO"]:
            risk_level = detected_risk
        elif moderation_complete and vision_complete:
            risk_level = "BAIXO"
        else:
            risk_level = "INDEFINIDO"

        flagged = flagged or risk_level in {"MEDIO", "ALTO", "CRITICO"}
        status = status_from_risk(risk_level)
        if not moderation_complete or not vision_complete:
            if risk_level in {"INDEFINIDO", "BAIXO"}:
                status = "REVISAO"

        if categories.get("nkata/sexual_services_solicitation"):
            note_parts.append("Possível oferta/solicitação de serviços sexuais detectada.")
        if any(categories.get(f"nkata/{key}") for key in (
            "contact_phone", "contact_email", "contact_username", "contact_url", "qr_code",
        )):
            note_parts.append("Possível tentativa de partilhar contactos ou ligação externa detectada.")
        if categories.get("nkata/advertising_or_sales"):
            note_parts.append("Possível publicidade ou venda detectada.")

    defaults = {
        "media_type": media_type,
        "provider": "+".join(dict.fromkeys(provider_parts))[:32],
        "model_name": ", ".join(dict.fromkeys(model_names))[:80],
        "status": status,
        "risk_level": risk_level,
        "flagged": flagged,
        "file_sha256": file_sha256,
        "media_bytes": media_bytes,
        "image_width": width,
        "image_height": height,
        "categories": categories,
        "category_scores": category_scores,
        "notes": " ".join(note_parts)[:500],
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
    vision_enabled = bool(getattr(settings, "NKATA_MEDIA_VISION_SCAN_ENABLED", False))
    if provider == "openai" and vision_enabled:
        return "OpenAI Moderation + inspeção visual + OpenCV"
    if provider == "openai":
        return "OpenAI Moderation + OpenCV"
    if vision_enabled:
        return "Inspeção visual + OpenCV"
    return "OpenCV local + revisão humana"
