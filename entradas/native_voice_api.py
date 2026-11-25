"""Private voice notes for accepted conversations, sharing the text timeline."""
import logging
import uuid
from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .audio_validation import prepare_voice_note, InvalidVoiceNote, AudioDecoderUnavailable
from .chat_media_api import _validate_audio, MAX_AUDIO_DURATION_SECONDS
from .conversations_api import accessible_thread, lock_pair, notify
from .credit_catalog import VOICE_NOTE_CREDITS
from .models import Conversa, MatchPerfil, MensagemMatch, NotaVozConversaNKATA, MovimentoCreditoNKATA
from .serializers import MensagemMatchSerializer
from .wallet_service import credit_spending_enabled, credit_balance, record_movement, WalletError

logger = logging.getLogger(__name__)


class VoiceStorageError(Exception):
    pass


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_voice(request, conversation_id):
    chat, me, other = accessible_thread(request, conversation_id)
    try:
        key = str(uuid.UUID(str(request.data.get("key"))))
    except (ValueError, TypeError, AttributeError):
        return Response({"detail":"Chave de operação inválida."},status=400)
    if str(request.data.get("expected_cost")) != str(VOICE_NOTE_CREDITS):
        return Response({"detail":"Confirme o custo de 2 créditos."},status=409)
    def replay():
        movement = MovimentoCreditoNKATA.objects.filter(carteira__usuario=request.user,chave=f"voice:{key}").first()
        if not movement:
            return None
        note = getattr(movement,"nota_voz_conversa",None)
        if not note or note.mensagem.conversa_id != chat.pk:
            return Response({"detail":"Chave já utilizada noutra operação."},status=409)
        return Response(MensagemMatchSerializer(note.mensagem,context={"request":request}).data,status=200)
    previous = replay()
    if previous is not None:
        return previous
    if not credit_spending_enabled():
        return Response({"detail":"Notas de voz indisponíveis."},status=403)
    if credit_balance(request.user) < VOICE_NOTE_CREDITS:
        return Response({"detail":"Saldo insuficiente."},status=409)
    upload = request.FILES.get("audio")
    try:
        duration = int(round(float(request.data.get("duracao_segundos",0))))
    except (TypeError, ValueError, OverflowError):
        duration = 0
    error = _validate_audio(upload,duration)
    if error:
        return Response({"audio":[error]},status=400)
    try:
        audio,duration = prepare_voice_note(upload, MAX_AUDIO_DURATION_SECONDS)
    except InvalidVoiceNote as error:
        return Response({"audio":[str(error)]},status=400)
    except AudioDecoderUnavailable as error:
        return Response({"detail":str(error)},status=503)
    note = None
    stored = False
    try:
        with transaction.atomic():
            other,_ = lock_pair(me,other.pk)
            user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if chat.match_origem_id:
                MatchPerfil.objects.select_for_update().get(pk=chat.match_origem_id)
            chat = get_object_or_404(Conversa.objects.select_for_update(),pk=chat.pk,estado=Conversa.ESTADO_ATIVA)
            previous = replay()
            if previous is not None:
                return previous
            if not credit_spending_enabled():
                return Response({"detail":"Notas de voz indisponíveis."},status=403)
            movement = record_movement(user,key=f"voice:{key}",kind="CONSUMO",amount=-VOICE_NOTE_CREDITS,
                reference=f"conversa:{chat.pk}",reason="Nota de voz")
            message = MensagemMatch.objects.create(conversa=chat,match=chat.match_origem,remetente=user,tipo="AUDIO",texto="")
            note = NotaVozConversaNKATA(mensagem=message,movimento=movement,duracao_segundos=duration)
            try:
                note.audio.save(audio.name,audio,save=False)
                stored = True
            except Exception as error:
                # Private storage can raise provider-specific errors (e.g. S3).
                # Roll back the ledger and message for any storage failure.
                raise VoiceStorageError() from error
            note.save()
            notify(other,me,"MENSAGEM",f"chat-msg:{chat.pk}","Nova nota de voz",f"{me.nome_publico} enviou-lhe uma nota de voz.")
    except WalletError as error:
        return Response({"detail":str(error)},status=409)
    except (DatabaseError,OSError,VoiceStorageError):
        if stored and note and note.audio and note.audio.name:
            try:
                note.audio.storage.delete(note.audio.name)
            except Exception:
                logger.exception("Falha ao limpar áudio não confirmado.")
        return Response({"detail":"Não foi possível guardar a nota de voz. Nenhum débito foi confirmado."},status=503)
    return Response(MensagemMatchSerializer(message,context={"request":request}).data,status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def voice_media(request, conversation_id, message_id):
    chat,_,_ = accessible_thread(request,conversation_id)
    note = get_object_or_404(NotaVozConversaNKATA.objects.filter(mensagem__conversa=chat,
        mensagem__apagada_em__isnull=True),mensagem_id=message_id)
    try:
        handle = note.audio.open("rb")
    except (OSError,ValueError):
        return Response({"detail":"Áudio indisponível."},status=404)
    response = FileResponse(handle,content_type="audio/wav")
    response["Content-Disposition"] = 'inline; filename="nota-de-voz.wav"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
