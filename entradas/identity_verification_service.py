import hashlib
from decimal import Decimal

import cv2
import numpy as np
from django.conf import settings
from django.utils import timezone

from .identity_models import VerificacaoIdentidadeNKATA


CAPTURE_ORDER = (
    "bi_frente",
    "bi_verso",
    "selfie_ao_vivo",
    "selfie_desafio",
)

CAPTURE_LABELS = {
    "bi_frente": "BI — frente",
    "bi_verso": "BI — verso",
    "selfie_ao_vivo": "Selfie frontal",
    "selfie_desafio": "Selfie do desafio",
}


def file_sha256(upload):
    upload.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: upload.read(1024 * 1024), b""):
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def _decode_image(upload):
    upload.seek(0)
    raw = upload.read()
    upload.seek(0)
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Não foi possível analisar a imagem.")
    return image


def _face_count(image):
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    minimum = max(36, min(gray.shape[:2]) // 10)
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(minimum, minimum),
    )
    return len(faces)


def inspect_identity_capture(upload, capture_type):
    if capture_type not in CAPTURE_ORDER:
        raise ValueError("Tipo de captura desconhecido.")

    image = _decode_image(upload)
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    glare_ratio = float(np.mean(gray >= 248))

    is_selfie = capture_type.startswith("selfie")
    min_width = 480 if is_selfie else 720
    min_height = 480 if is_selfie else 440
    min_sharpness = 32.0 if is_selfie else 42.0
    min_contrast = 14.0 if is_selfie else 17.0
    faces = _face_count(image) if is_selfie else None

    checks = {
        "resolution": width >= min_width and height >= min_height,
        "brightness": 42.0 <= brightness <= 225.0,
        "contrast": contrast >= min_contrast,
        "sharpness": sharpness >= min_sharpness,
        "glare": glare_ratio <= 0.20,
    }
    if is_selfie:
        checks["single_face"] = faces == 1

    messages = []
    if not checks["resolution"]:
        messages.append("Aproxime a câmara e use uma imagem com maior resolução.")
    if brightness < 42.0:
        messages.append("Procure um local com mais luz.")
    elif brightness > 225.0:
        messages.append("A imagem está demasiado clara. Evite luz direta.")
    if not checks["contrast"]:
        messages.append("A imagem tem pouco detalhe. Limpe a lente e melhore a iluminação.")
    if not checks["sharpness"]:
        messages.append("Mantenha o telefone firme; a imagem está desfocada.")
    if not checks["glare"]:
        messages.append("Incline ligeiramente o documento para retirar os reflexos.")
    if is_selfie and faces != 1:
        messages.append(
            "Mantenha apenas um rosto, completamente visível, dentro da moldura."
        )

    passed = sum(1 for value in checks.values() if value)
    score = round((passed / max(1, len(checks))) * 100)
    return {
        "accepted": all(checks.values()),
        "score": score,
        "checks": checks,
        "messages": messages,
        "metrics": {
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "sharpness": round(sharpness, 2),
            "glare_ratio": round(glare_ratio, 4),
            "faces": faces,
        },
        "sha256": file_sha256(upload),
    }


def next_capture(session):
    for capture_type in CAPTURE_ORDER:
        if not getattr(session, capture_type):
            return capture_type
    return "concluida"


def _read_field_bytes(field_file):
    with field_file.open("rb") as handle:
        return handle.read()


def _aws_face_similarity(session):
    if not getattr(settings, "NKATA_ID_AWS_REKOGNITION_ENABLED", False):
        return None
    try:
        import boto3

        client = boto3.client(
            "rekognition",
            region_name=getattr(settings, "NKATA_ID_AWS_REGION", None) or None,
        )
        result = client.compare_faces(
            SourceImage={"Bytes": _read_field_bytes(session.bi_frente)},
            TargetImage={"Bytes": _read_field_bytes(session.selfie_ao_vivo)},
            SimilarityThreshold=float(
                getattr(settings, "NKATA_ID_FACE_MATCH_THRESHOLD", 90.0)
            ),
            QualityFilter="AUTO",
        )
    except Exception as exc:  # provider failure must never expose secrets to users
        signals = dict(session.sinais_risco or {})
        signals["provider_error"] = exc.__class__.__name__
        session.sinais_risco = signals
        return None

    matches = result.get("FaceMatches") or []
    if not matches:
        return Decimal("0.00")
    similarity = max(float(item.get("Similarity", 0.0)) for item in matches)
    return Decimal(str(round(similarity, 2)))


def finalize_identity_analysis(session):
    if not session.capturas_completas:
        session.etapa_atual = next_capture(session)
        session.status = "EM_CAPTURA"
        session.save(update_fields=["etapa_atual", "status", "atualizado_em"])
        return session

    session.status = "A_ANALISAR"
    checks = session.verificacoes_imagem or {}
    front = checks.get("bi_frente", {})
    neutral = checks.get("selfie_ao_vivo", {})
    challenge = checks.get("selfie_desafio", {})
    session.documento_sha256 = front.get("sha256", "")
    session.selfie_sha256 = neutral.get("sha256", "")

    duplicate_document = bool(
        session.documento_sha256
        and VerificacaoIdentidadeNKATA.objects.exclude(pk=session.pk).filter(
            documento_sha256=session.documento_sha256,
            status__in={"APROVADA", "REVISAO", "A_ANALISAR"},
        ).exists()
    )
    different_selfies = bool(
        neutral.get("sha256")
        and challenge.get("sha256")
        and neutral.get("sha256") != challenge.get("sha256")
    )
    session.vivacidade_confirmada = bool(
        different_selfies
        and neutral.get("metrics", {}).get("faces") == 1
        and challenge.get("metrics", {}).get("faces") == 1
    )

    face_similarity = _aws_face_similarity(session)
    session.correspondencia_facial = face_similarity
    if face_similarity is not None:
        session.provedor_biometrico = "aws_rekognition"

    threshold = Decimal(
        str(getattr(settings, "NKATA_ID_FACE_MATCH_THRESHOLD", 90.0))
    )
    risk_score = 0
    signals = dict(session.sinais_risco or {})
    signals.update({
        "documento_reutilizado": duplicate_document,
        "selfies_diferentes": different_selfies,
        "sequencia_ao_vivo": session.vivacidade_confirmada,
        "comparacao_facial_disponivel": face_similarity is not None,
    })

    if duplicate_document:
        risk_score += 70
    if not session.vivacidade_confirmada:
        risk_score += 35
    if face_similarity is not None and face_similarity < threshold:
        risk_score += 60

    session.pontuacao_risco = min(risk_score, 100)
    session.sinais_risco = signals
    session.etapa_atual = "concluida"

    if duplicate_document or (face_similarity is not None and face_similarity < threshold):
        session.status = "REVISAO"
        session.risco = "ALTO"
    elif (
        face_similarity is not None
        and face_similarity >= threshold
        and session.vivacidade_confirmada
    ):
        session.status = "APROVADA"
        session.risco = "BAIXO"
        session.decisao_origem = "AUTOMATICA"
        session.analisado_em = timezone.now()
    else:
        session.status = "REVISAO"
        session.risco = "MEDIO" if not session.vivacidade_confirmada else "BAIXO"

    session.save()
    return session
