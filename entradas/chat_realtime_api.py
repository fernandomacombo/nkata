from datetime import timedelta

from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .chat_media_api import serialize_audio_message
from .chat_realtime_models import EstadoConversaNKATA
from .models import MatchPerfil
from .serializers import MensagemMatchSerializer


TYPING_TTL_SECONDS = 5
PRESENCE_TTL_SECONDS = 20
INITIAL_SYNC_SECONDS = 30
MAX_RECEIPT_IDS = 200


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
        .select_related(
            "perfil_1",
            "perfil_1__usuario",
            "perfil_2",
            "perfil_2__usuario",
        )
        .first()
    )


def _other_user_id(match, current_user_id):
    if match.perfil_1.usuario_id == current_user_id:
        return match.perfil_2.usuario_id
    if match.perfil_2.usuario_id == current_user_id:
        return match.perfil_1.usuario_id
    return None


def _parse_since(value, snapshot_time):
    parsed = parse_datetime(str(value or "").strip()) if value else None
    if parsed is None:
        return snapshot_time - timedelta(seconds=INITIAL_SYNC_SECONDS)
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    if parsed > snapshot_time:
        return snapshot_time - timedelta(seconds=2)
    return parsed


def _touch_state(match, user, *, typing=None, now=None):
    now = now or timezone.now()
    try:
        state, _created = EstadoConversaNKATA.objects.get_or_create(
            match=match,
            usuario=user,
            defaults={
                "is_typing": bool(typing) if typing is not None else False,
                "typing_updated_at": now if typing is not None else None,
                "last_seen_at": now,
            },
        )
        update_fields = ["last_seen_at"]
        state.last_seen_at = now
        if typing is not None:
            state.is_typing = bool(typing)
            state.typing_updated_at = now
            update_fields.extend(["is_typing", "typing_updated_at"])
        state.save(update_fields=update_fields)
        return state
    except DatabaseError:
        return None


def _presence_payload(match, user, snapshot_time):
    other_user_id = _other_user_id(match, user.id)
    if not other_user_id:
        return {
            "typing": False,
            "active": False,
            "setup_required": False,
        }

    try:
        state = EstadoConversaNKATA.objects.filter(
            match=match,
            usuario_id=other_user_id,
        ).first()
    except DatabaseError:
        return {
            "typing": False,
            "active": False,
            "setup_required": True,
        }

    if not state:
        return {
            "typing": False,
            "active": False,
            "setup_required": False,
        }

    typing_fresh = bool(
        state.is_typing
        and state.typing_updated_at
        and state.typing_updated_at
        >= snapshot_time - timedelta(seconds=TYPING_TTL_SECONDS)
    )
    active_fresh = bool(
        state.last_seen_at
        and state.last_seen_at
        >= snapshot_time - timedelta(seconds=PRESENCE_TTL_SECONDS)
    )
    return {
        "typing": typing_fresh,
        "active": active_fresh,
        "setup_required": False,
    }


def _new_text_messages(request, match, since, snapshot_time):
    messages = (
        match.mensagens
        .filter(criado_em__gt=since, criado_em__lte=snapshot_time)
        .select_related("remetente", "remetente__perfil_nkata")
        .order_by("criado_em", "id")
    )
    return MensagemMatchSerializer(
        messages,
        many=True,
        context={"request": request},
    ).data


def _new_audio_messages(request, match, since, snapshot_time):
    try:
        messages = (
            match.mensagens_audio_nkata
            .filter(criado_em__gt=since, criado_em__lte=snapshot_time)
            .select_related("remetente", "remetente__perfil_nkata")
            .order_by("criado_em", "id")
        )
        return [serialize_audio_message(request, message) for message in messages]
    except DatabaseError:
        return []


def _mark_incoming_read(match, user):
    match.mensagens.filter(lida=False).exclude(remetente=user).update(lida=True)
    try:
        match.mensagens_audio_nkata.filter(lida=False).exclude(remetente=user).update(lida=True)
    except DatabaseError:
        pass


def _read_receipts(match, user):
    text_ids = list(
        match.mensagens
        .filter(remetente=user, lida=True)
        .order_by("-id")
        .values_list("id", flat=True)[:MAX_RECEIPT_IDS]
    )
    try:
        audio_ids = list(
            match.mensagens_audio_nkata
            .filter(remetente=user, lida=True)
            .order_by("-id")
            .values_list("id", flat=True)[:MAX_RECEIPT_IDS]
        )
    except DatabaseError:
        audio_ids = []
    return {"text": text_ids, "audio": audio_ids}


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_chat_live(request, match_id):
    match = _match_do_utilizador(request.user, match_id)
    if not match:
        return Response({"detail": "Conversa não encontrada."}, status=404)

    snapshot_time = timezone.now()

    if request.method == "POST":
        raw_typing = request.data.get("typing", False)
        typing = raw_typing if isinstance(raw_typing, bool) else str(raw_typing).lower() in {
            "1", "true", "yes", "on",
        }
        state = _touch_state(
            match,
            request.user,
            typing=typing,
            now=snapshot_time,
        )
        if state is None:
            return Response(
                {
                    "detail": "O estado em tempo real do chat ainda precisa de ser preparado.",
                    "setup_required": True,
                },
                status=503,
            )
        return Response({
            "ok": True,
            "typing": bool(state.is_typing),
            "server_time": snapshot_time.isoformat(),
        })

    current_state = _touch_state(match, request.user, now=snapshot_time)
    since = _parse_since(request.query_params.get("since"), snapshot_time)
    _mark_incoming_read(match, request.user)

    text_messages = list(_new_text_messages(request, match, since, snapshot_time))
    audio_messages = _new_audio_messages(request, match, since, snapshot_time)
    results = [*text_messages, *audio_messages]
    results.sort(key=lambda item: str(item.get("criado_em") or ""))

    presence = _presence_payload(match, request.user, snapshot_time)
    return Response({
        "results": results,
        "presence": {
            "typing": presence["typing"],
            "active": presence["active"],
        },
        "read_receipts": _read_receipts(match, request.user),
        "server_time": snapshot_time.isoformat(),
        "setup_required": bool(current_state is None or presence["setup_required"]),
    })
