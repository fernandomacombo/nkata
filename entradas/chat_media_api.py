import mimetypes
import os
import uuid
import logging

from django.db import DatabaseError, transaction
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import FileResponse
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .chat_permissions import ChatIdentityPermission, legacy_chat_allowed
from .credit_catalog import VOICE_NOTE_CREDITS
from .wallet_service import credit_spending_enabled, credit_balance, record_movement, WalletError
from .chat_media_models import MensagemAudioMatchNKATA
from .models import MatchPerfil, PerfilNKATA, Conversa, EnvioAudioCreditoNKATA
from .plan_service import plan_for_user
from .user_roles import active_member_profile_for_user
from .audio_validation import prepare_voice_note, InvalidVoiceNote, AudioDecoderUnavailable


logger = logging.getLogger(__name__)

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
    return active_member_profile_for_user(user)


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


def voice_credit_offer(user, included):
    return {"enabled": credit_spending_enabled(), "cost": 0 if included else VOICE_NOTE_CREDITS,
            "balance": credit_balance(user) if credit_spending_enabled() else 0}


def chat_capabilities(user):
    plan = plan_for_user(user)
    return {
        "plan": plan["code"],
        "plan_label": plan["label"],
        "text_enabled": bool(plan["features"].get("chat_text", True)),
        "audio_enabled": bool(plan["features"].get("chat_audio", False)),
        "video_enabled": bool(plan["features"].get("chat_video", False)),
        "max_audio_seconds": MAX_AUDIO_DURATION_SECONDS,
        "voice_credit": voice_credit_offer(user, plan["features"].get("chat_audio", False)),
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
@permission_classes([permissions.IsAuthenticated, ChatIdentityPermission])
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

    if not capabilities["audio_enabled"] and not capabilities.get("voice_credit", {}).get("enabled"):
        return Response(
            {
                "detail": "Notas de voz indisponíveis neste momento.",
                "code": "paid_plan_required_for_chat_audio",
                "capabilities": capabilities,
            },
            status=403,
        )

    audio = request.FILES.get("audio")
    try:
        duration_seconds = int(round(float(request.data.get("duracao_segundos", 0) or 0)))
    except (TypeError, ValueError, OverflowError):
        duration_seconds = 0

    error = _validate_audio(audio, duration_seconds)
    if error:
        return Response({"audio": [error]}, status=400)

    try:
        audio, duration_seconds = prepare_voice_note(audio, MAX_AUDIO_DURATION_SECONDS)
    except InvalidVoiceNote as error:
        return Response({"audio": [str(error)]}, status=400)
    except AudioDecoderUnavailable as error:
        return Response({"detail": str(error)}, status=503)

    message = None
    try:
        with transaction.atomic():
            list(PerfilNKATA.objects.select_for_update().filter(
                pk__in=[match.perfil_1_id, match.perfil_2_id]).order_by("pk"))
            user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
            match = MatchPerfil.objects.select_for_update().get(pk=match.pk)
            if not Conversa.objects.select_for_update().filter(match_origem=match, estado=Conversa.ESTADO_ATIVA).first() or not legacy_chat_allowed(user, match):
                return Response({"detail": "Conversa indisponível."}, status=404)
            included = plan_for_user(user)["features"].get("chat_audio", False)
            key = None
            raw_key = request.data.get("key")
            if raw_key:
                try:
                    key = str(uuid.UUID(str(raw_key)))
                except (ValueError, TypeError, AttributeError):
                    return Response({"detail": "Chave de operação inválida."}, status=400)
                receipt = EnvioAudioCreditoNKATA.objects.filter(movimento__carteira__usuario=user,
                    movimento__chave=f"voice:{key}").first()
                if receipt:
                    if receipt.match_id != match.pk:
                        return Response({"detail": "Chave já utilizada noutra conversa."}, status=409)
                    existing = MensagemAudioMatchNKATA.objects.filter(pk=receipt.audio_id, match=match, remetente=user).first()
                    if not existing:
                        return Response({"detail": "Nota de voz anteriormente enviada; consulte o histórico."}, status=409)
                    return Response(serialize_audio_message(request, existing), status=200)
            movement = None
            if not included:
                if not credit_spending_enabled():
                    return Response({"detail": "Notas de voz exigem acesso pago.", "code": "paid_plan_required_for_chat_audio"}, status=403)
                # Multipart carries the confirmed integer as a string.
                expected = request.data.get("expected_cost")
                if not key or str(expected) != str(VOICE_NOTE_CREDITS):
                    return Response({"detail": "Confirme o custo atual da nota de voz.", "voice_credit": voice_credit_offer(user, False)}, status=409)
                try:
                    movement = record_movement(user, key=f"voice:{key}", kind="CONSUMO",
                        amount=-VOICE_NOTE_CREDITS, reference=f"match:{match.pk}", reason="Nota de voz")
                except WalletError as error:
                    return Response({"detail": str(error), "voice_credit": voice_credit_offer(user, False)}, status=409)
            message = MensagemAudioMatchNKATA.objects.create(
                match=match, remetente=user, audio=audio, duracao_segundos=duration_seconds)
            if movement:
                EnvioAudioCreditoNKATA.objects.create(movimento=movement, audio_id=message.pk, match_id=match.pk)
            match.save(update_fields=["atualizado_em"])
    except (DatabaseError, OSError):
        # If database commit failed after writing media, remove the orphan file.
        if message and message.audio and message.audio.name:
            try:
                message.audio.storage.delete(message.audio.name)
            except Exception:
                logger.exception("Falha ao limpar nota de voz não confirmada.")
        return Response(
            {
                "detail": "As notas de voz ainda precisam de ser preparadas neste ambiente.",
                "setup_required": True,
            },
            status=503,
        )

    return Response(serialize_audio_message(request, message), status=201)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, ChatIdentityPermission])
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
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
