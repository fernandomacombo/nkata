import mimetypes
import os

from django.db import DatabaseError
from django.db.models import Q
from django.http import FileResponse
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .chat_media_models import MensagemAudioMatchNKATA
from .models import MatchPerfil
from .plan_service import plan_for_user


MAX_AUDIO_SIZE = 12 * 1024 * 1024
MAX_AUDIO_DURATION_SECONDS = 180
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".m4a", ".mp4", ".ogg", ".mp3", ".wav"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/x-m4a",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "video/webm",
}


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


def _match_do_utilizador(user, match_id):
    perfil = _perfil_do_utilizador(user)
    if not perfil:
        return None
    return (
        MatchPerfil.objects
        .filter(
            Q(perfil_1=perfil) | Q(perfil_2=perfil),
            id=match_id,
            status="ATIVO",
        )
        .select_related("perfil_1", "perfil_2")
        .first()
    )


def chat_capabilities(user):
    plan = plan_for_user(user)
    return {
        "plan": plan["code"],
        "plan_label": plan["label"],
        "text_enabled": bool(plan["features"].get("chat_text", True)),
        "audio_enabled": bool(plan["features"].get("chat_audio", False)),
        "video_enabled": bool(plan["features"].get("chat_video", False)),
        "max_audio_seconds": MAX_AUDIO_DURATION_SECONDS,
    }


def serialize_audio_message(request, message):
    return {
        "id": f"audio-{message.id}",
        "audio_id": message.id,
        "match": message.match_id,
        "remetente_id": message.remetente_id,
        "remetente_nome": (
            getattr(getattr(message.remetente, "perfil_nkata", None), "nome_publico", None)
            or getattr(message.remetente, "first_name", "")
            or "Membro NKATA"
        ),
        "texto": "",
        "tipo": "AUDIO",
        "audio_url": request.build_absolute_uri(
            f"/api/minha-conta/matches/{message.match_id}/audio/{message.id}/media/"
        ),
        "duracao_segundos": int(message.duracao_segundos or 0),
        "lida": bool(message.lida),
        "minha": message.remetente_id == request.user.id,
        "criado_em": message.criado_em,
    }


def _validate_audio(file_obj, duration_seconds):
    if not file_obj:
        return "Grave uma nota de voz antes de enviar."

    extension = os.path.splitext(file_obj.name or "")[1].lower()
    content_type = str(getattr(file_obj, "content_type", "") or "").lower().split(";", 1)[0].strip()

    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        return "Formato de áudio não suportado. Grave novamente a nota de voz."
    if content_type and content_type not in ALLOWED_AUDIO_CONTENT_TYPES:
        return "O ficheiro enviado não foi reconhecido como uma nota de voz válida."
    if file_obj.size <= 0 or file_obj.size > MAX_AUDIO_SIZE:
        return "A nota de voz deve ter no máximo 12 MB."
    if duration_seconds < 1 or duration_seconds > MAX_AUDIO_DURATION_SECONDS:
        return f"A nota de voz deve ter entre 1 e {MAX_AUDIO_DURATION_SECONDS} segundos."
    return None


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_audios_match(request, match_id):
    match = _match_do_utilizador(request.user, match_id)
    if not match:
        return Response({"detail": "Conversa não encontrada."}, status=404)

    capabilities = chat_capabilities(request.user)

    if request.method == "GET":
        try:
            match.mensagens_audio_nkata.filter(
                lida=False,
            ).exclude(remetente=request.user).update(lida=True)
            messages = match.mensagens_audio_nkata.select_related(
                "remetente",
                "remetente__perfil_nkata",
            ).all()
        except DatabaseError:
            return Response({
                "results": [],
                "capabilities": capabilities,
                "setup_required": True,
            })

        return Response({
            "results": [serialize_audio_message(request, message) for message in messages],
            "capabilities": capabilities,
            "setup_required": False,
        })

    if not capabilities["audio_enabled"]:
        return Response(
            {
                "detail": "Notas de voz estão disponíveis no NKATA Essencial e Premium.",
                "code": "paid_plan_required_for_chat_audio",
                "capabilities": capabilities,
            },
            status=403,
        )

    audio = request.FILES.get("audio")
    try:
        duration_seconds = int(round(float(request.data.get("duracao_segundos", 0) or 0)))
    except (TypeError, ValueError):
        duration_seconds = 0

    error = _validate_audio(audio, duration_seconds)
    if error:
        return Response({"audio": [error]}, status=400)

    try:
        message = MensagemAudioMatchNKATA.objects.create(
            match=match,
            remetente=request.user,
            audio=audio,
            duracao_segundos=duration_seconds,
        )
        match.save(update_fields=["atualizado_em"])
    except DatabaseError:
        return Response(
            {
                "detail": "As notas de voz ainda precisam de ser preparadas neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    return Response(serialize_audio_message(request, message), status=201)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_media_audio_match(request, match_id, audio_id):
    match = _match_do_utilizador(request.user, match_id)
    if not match:
        return Response({"detail": "Áudio não disponível."}, status=404)

    try:
        message = MensagemAudioMatchNKATA.objects.filter(
            id=audio_id,
            match=match,
        ).first()
    except DatabaseError:
        return Response({"detail": "Áudio não disponível."}, status=404)

    if not message or not message.audio:
        return Response({"detail": "Áudio não disponível."}, status=404)

    try:
        handle = message.audio.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        return Response({"detail": "Áudio não disponível."}, status=404)

    content_type = mimetypes.guess_type(message.audio.name)[0] or "application/octet-stream"
    response = FileResponse(handle, content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(message.audio.name)}"'
    response["Cache-Control"] = "private, max-age=120"
    response["X-Content-Type-Options"] = "nosniff"
    return response
