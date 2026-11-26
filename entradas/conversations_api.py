from datetime import timedelta
from functools import partial

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .chat_permissions import chat_pair_allowed, request_pair_allowed, conversation_consent_state, conversation_has_access
from .credit_catalog import ICEBREAKERS, ICEBREAKER_DAILY_LIMIT
from .legacy_commercial import credit_only_enabled
from .wallet_service import unlock_chat, chat_credit_snapshot, WalletError
from .signal_views import _availability_payload, send_signal
from django.contrib.auth import get_user_model
from .identity_models import pedido_tem_identidade_verificada
from .models import AcaoPerfil, Conversa, MatchPerfil, MensagemMatch, PedidoConversa, PerfilNKATA
from .profile_media_api import profile_photo_url
from .chat_media_models import MensagemAudioMatchNKATA
from .chat_media_api import voice_credit_offer
from .call_models import ChamadaMatchNKATA
from .call_history_api import serialize_call_message
from .notification_models import NotificacaoNKATA
from .plan_service import can_send_chat_text, plan_for_user, preset_snapshot, chat_message_type
from .serializers import MensagemMatchSerializer
from .user_roles import active_member_profile_for_user


def member(request, *, require_identity=True):
    profile = active_member_profile_for_user(request.user)
    if not profile or (require_identity and not pedido_tem_identidade_verificada(profile.pedido)):
        raise PermissionDenied("Verifique a sua identidade para usar os chats.")
    return profile


def available(me, other):
    return chat_pair_allowed(me, other)


def lock_pair(me, other_id, *, for_request=False, for_send=False):
    # All mutations acquire the same two rows in the same order, including the
    # first request, when there is no request or conversation row to lock yet.
    profiles = list(PerfilNKATA.objects.select_for_update().filter(
        pk__in=[me.pk, other_id]).order_by("pk"))
    if len(profiles) != 2:
        raise NotFound("Perfil indisponível.")
    other = next(profile for profile in profiles if profile.pk != me.pk)
    current = next(profile for profile in profiles if profile.pk == me.pk)
    allowed = request_pair_allowed if for_request or (for_send and credit_only_enabled()) else available
    if not allowed(current, other):
        raise NotFound("Perfil indisponível.")
    if for_send and not pedido_tem_identidade_verificada(current.pedido):
        raise PermissionDenied("Verifique a sua identidade para enviar mensagens.")
    return other, {"perfil_1": profiles[0], "perfil_2": profiles[1]}


def notify(other, me, kind, key, title, body):
    transaction.on_commit(partial(
        NotificacaoNKATA.objects.update_or_create,
        destinatario_id=other.usuario_id, chave=key,
        defaults=dict(ator_id=me.usuario_id, perfil_id=me.pk, tipo=kind,
                      titulo=title, texto=body, lida=False),
    ), robust=True)


def chat_profile(profile):
    return {"id": profile.pk, "nome_publico": profile.nome_publico,
            "foto_url": profile_photo_url(profile) if profile.visivel else None}


def request_payload(item, me, now):
    received = item.destinatario_id == me.pk
    other = item.remetente if received else item.destinatario
    state = "EXPIRADO" if item.estado == "PENDENTE" and item.expira_em <= now else item.estado
    return {"id": item.pk, "recebido": received, "nome": other.nome_publico, "perfil": chat_profile(other),
            "estado": state, "criado_em": item.criado_em, "expira_em": item.expira_em,
            "identity_pending": not available(me, other),
            "decidido_em": item.decidido_em,
            "conversation_id": item.conversa_id if item.conversa_id and item.conversa.estado == Conversa.ESTADO_ATIVA else None,
            "segundos_restantes": max(0, int((item.expira_em - now).total_seconds())) if state == "PENDENTE" else 0}


def clear_request_notice(item):
    NotificacaoNKATA.objects.filter(destinatario_id=item.destinatario.usuario_id,
                                     chave=f"pedido-chat:{item.pk}").update(lida=True)


def accept(pending, pair, now):
    chat, _ = Conversa.objects.get_or_create(**pair)
    pending.estado = "ACEITE"
    pending.decidido_em = now
    pending.conversa = chat
    pending.save(update_fields=["estado", "decidido_em", "conversa"])
    clear_request_notice(pending)
    notify(pending.remetente, pending.destinatario, "CHAT_ACEITE", f"chat-aceite:{chat.pk}",
           "Pedido de conversa aceite", "Pedido aceite. Pode ler mensagens gratuitamente; verifique a sua identidade para enviar.")
    return Response({"estado": "ACEITE", "conversation_id": chat.pk,
                     "identity_pending": not available(pending.remetente, pending.destinatario)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def send_request(request, profile_id):
    me = member(request, require_identity=False)
    other, pair = lock_pair(me, profile_id, for_request=True)
    if not other.visivel:
        raise NotFound("Perfil indisponível.")
    existing = Conversa.objects.filter(**pair).first()
    if existing:
        if existing.estado != Conversa.ESTADO_ATIVA:
            raise NotFound("Conversa indisponível.")
        consent = conversation_consent_state(existing)
        if consent != "SEM_PEDIDO":
            return Response({"estado": consent, "conversation_id": existing.pk,
                             "identity_pending": not available(me, other)})
    requests = PedidoConversa.objects.filter(
        Q(remetente=me, destinatario=other) | Q(remetente=other, destinatario=me))
    now = timezone.now()
    expired = requests.filter(estado="PENDENTE", expira_em__lte=now)
    for item in expired.select_related("destinatario"):
        clear_request_notice(item)
    expired.update(estado="EXPIRADO")
    pending = requests.filter(estado="PENDENTE").first()
    if pending and pending.remetente_id == me.pk:
        return Response(request_payload(pending, me, now))
    refusal = requests.filter(remetente=me, estado="RECUSADO", decidido_em__gt=now-timedelta(days=30)).order_by("-decidido_em").first()
    if refusal:
        return Response({"detail": "Pode voltar a pedir conversa 30 dias após a recusa.",
                         "pode_pedir_em": refusal.decidido_em + timedelta(days=30)}, status=409)
    if pending and pending.destinatario_id == me.pk:
        return accept(pending, pair, now)
    pending = requests.create(remetente=me, destinatario=other, expira_em=now+timedelta(days=7))
    notify(other, me, "PEDIDO_CHAT", f"pedido-chat:{pending.pk}", "Novo pedido de conversa",
           f"{me.nome_publico} gostaria de conversar consigo.")
    return Response(request_payload(pending, me, now), status=201)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def decide_request(request, request_id):
    me = member(request, require_identity=False)
    pending = get_object_or_404(PedidoConversa.objects.filter(Q(remetente=me) | Q(destinatario=me)), pk=request_id)
    if request.method == "GET":
        other = pending.remetente if pending.destinatario_id == me.pk else pending.destinatario
        if not request_pair_allowed(me, other):
            raise NotFound("Pedido indisponível.")
        return Response(request_payload(pending, me, timezone.now()))
    if pending.destinatario_id != me.pk:
        raise NotFound("Pedido indisponível.")
    _, pair = lock_pair(me, pending.remetente_id, for_request=True)
    pending.refresh_from_db()
    now = timezone.now()
    decision = request.data.get("decisao")
    if decision not in ("ACEITE", "RECUSADO"):
        raise ValidationError("Decisão inválida.")
    if pending.estado == "PENDENTE" and pending.expira_em <= now:
        pending.estado = "EXPIRADO"
        pending.save(update_fields=["estado"])
        clear_request_notice(pending)
    if pending.estado != "PENDENTE":
        return Response({"estado": pending.estado, "conversation_id": pending.conversa_id},
                        status=200 if pending.estado == decision else 409)
    if decision == "ACEITE":
        return accept(pending, pair, now)
    pending.estado = decision
    pending.decidido_em = now
    pending.save(update_fields=["estado", "decidido_em"])
    clear_request_notice(pending)
    return Response(request_payload(pending, me, now))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_request(request, request_id):
    me = member(request, require_identity=False)
    pending = get_object_or_404(PedidoConversa, pk=request_id, remetente=me)
    # Acquire the same pair locks as acceptance; cancellation is allowed even
    # when the recipient is no longer available or has blocked the sender.
    list(PerfilNKATA.objects.select_for_update().filter(pk__in=[me.pk, pending.destinatario_id]).order_by("pk"))
    pending = get_object_or_404(PedidoConversa, pk=request_id, remetente=me)
    now = timezone.now()
    if pending.estado == "PENDENTE":
        if pending.expira_em <= now:
            pending.estado = "EXPIRADO"
            pending.save(update_fields=["estado"])
        else:
            pending.estado = "CANCELADO"
            pending.decidido_em = now
            pending.save(update_fields=["estado", "decidido_em"])
        clear_request_notice(pending)
    return Response(request_payload(pending, me, now), status=200 if pending.estado == "CANCELADO" else 409)


def participants(me):
    return Conversa.objects.filter(Q(perfil_1=me) | Q(perfil_2=me),
                                  estado=Conversa.ESTADO_ATIVA).select_related("perfil_1__pedido", "perfil_2__pedido", "perfil_1__usuario", "perfil_2__usuario")


def legacy_match_id(chat):
    # Legacy audio/call endpoints still require an active Match.
    return chat.match_origem_id if chat.match_origem_id and chat.match_origem.status == "ATIVO" else None


def peer(chat, me):
    return chat.perfil_2 if chat.perfil_1_id == me.pk else chat.perfil_1


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inbox(request):
    me = member(request, require_identity=False)
    chats = []
    eligible = [(chat, peer(chat, me)) for chat in participants(me).select_related("match_origem").order_by("-pk")]
    permitted = [(chat, other) for chat, other in eligible if request_pair_allowed(me, other)]
    consent_states = {chat.pk: conversation_consent_state(chat) for chat, _ in permitted}
    permitted = [(chat, other) for chat, other in permitted if consent_states[chat.pk] != "SEM_PEDIDO"]
    eligible = permitted if credit_only_enabled() else [(chat, other) for chat, other in permitted if available(me, other)]
    # Accepted conversations remain visible as metadata only; no message previews,
    # unread counts, media or thread contents until both identities are verified.
    open_ids = {chat.pk for chat, _ in eligible}
    for chat, other in permitted:
        if chat.pk not in open_ids:
            chats.append({"id": chat.pk, "nome": other.nome_publico, "perfil": chat_profile(other),
                          "match_id": None, "ultima_mensagem": None, "nao_lidas": 0,
                          "textos_nao_lidos": 0, "audios_nao_lidos": 0,
                          "identity_pending": True, "consent_state": consent_states[chat.pk], "atividade_em": chat.criado_em})
    native_ids = [chat.pk for chat, _ in eligible if not chat.match_origem_id]
    match_ids = [chat.match_origem_id for chat, _ in eligible if chat.match_origem_id]
    media_ids = [legacy_match_id(chat) for chat, other in eligible if legacy_match_id(chat) and available(me, other)]

    def latest_by(queryset, key, date):
        rows = queryset.annotate(chat_rank=Window(expression=RowNumber(), partition_by=[F(key)],
            order_by=[F(date).desc(), F("pk").desc()])).filter(chat_rank=1)
        return {getattr(row, key): row for row in rows}

    def unread_by(queryset, key):
        return dict(queryset.filter(lida=False).exclude(remetente=request.user).order_by().values(key)
                    .annotate(total=Count("pk")).values_list(key, "total"))

    native = MensagemMatch.objects.filter(conversa_id__in=native_ids)
    legacy = MensagemMatch.objects.filter(match_id__in=match_ids)
    native_latest = latest_by(native, "conversa_id", "criado_em")
    legacy_latest = latest_by(legacy, "match_id", "criado_em")
    native_unread = unread_by(native.filter(apagada_em__isnull=True), "conversa_id")
    legacy_unread = unread_by(legacy.filter(apagada_em__isnull=True), "match_id")
    audio = MensagemAudioMatchNKATA.objects.filter(match_id__in=media_ids)
    audio_latest = latest_by(audio, "match_id", "criado_em")
    audio_unread = unread_by(audio, "match_id")
    call_latest = latest_by(ChamadaMatchNKATA.objects.filter(match_id__in=media_ids), "match_id", "atualizada_em")
    for chat, other in eligible:
        latest = legacy_latest.get(chat.match_origem_id) if chat.match_origem_id else native_latest.get(chat.pk)
        preview = None if latest is None else {
            "texto": "Mensagem apagada" if latest.apagada_em else ("Nota de voz" if latest.tipo == "AUDIO" else latest.texto[:160]),
            "minha": latest.remetente_id == request.user.pk,
            "criado_em": latest.criado_em,
        }
        unread_text = legacy_unread.get(chat.match_origem_id, 0) if chat.match_origem_id else native_unread.get(chat.pk, 0)
        unread_audio = 0
        legacy_id = legacy_match_id(chat) if available(me, other) else None
        # Only count media that can still be opened in the legacy workspace.
        if legacy_id:
            unread_audio = audio_unread.get(legacy_id, 0)
            last_audio = audio_latest.get(legacy_id)
            call = call_latest.get(legacy_id)
            if last_audio and (preview is None or last_audio.criado_em > preview["criado_em"]):
                preview = {"texto": "Nota de voz", "tipo": "AUDIO", "minha": last_audio.remetente_id == request.user.pk,
                           "criado_em": last_audio.criado_em}
            if call:
                item = serialize_call_message(call, request.user.pk)
                if preview is None or item["criado_em"] > preview["criado_em"]:
                    preview = {"texto": item["texto"], "tipo": "CALL", "minha": item["minha"], "criado_em": item["criado_em"]}
        chats.append({"id": chat.pk, "nome": other.nome_publico, "perfil": chat_profile(other),
                      "match_id": legacy_id, "ultima_mensagem": preview, "consent_state": consent_states[chat.pk],
                      "identity_pending": not pedido_tem_identidade_verificada(me.pedido),
                      "read_only": not pedido_tem_identidade_verificada(me.pedido),
                      "nao_lidas": unread_text + unread_audio, "textos_nao_lidos": unread_text,
                      "audios_nao_lidos": unread_audio,
                      "atividade_em": preview["criado_em"] if preview else chat.criado_em})
    chats.sort(key=lambda item: (item["atividade_em"], item["id"]), reverse=True)
    now = timezone.now()
    requests = PedidoConversa.objects.filter(Q(destinatario=me) | Q(remetente=me)).select_related(
        "remetente__usuario", "remetente__pedido", "destinatario__usuario", "destinatario__pedido", "conversa")
    active = Q(estado="PENDENTE", expira_em__gt=now)
    pending, history = [], []
    for rows, target in ((requests.filter(active), pending), (requests.exclude(active).order_by("-pk")[:50], history)):
        for item in rows:
            other = item.remetente if item.destinatario_id == me.pk else item.destinatario
            if request_pair_allowed(me, other):
                target.append(request_payload(item, me, now))
    # Connections are social interactions, not consent to a private chat.
    connections = {}
    active_chats = {item["perfil"]["id"]: item["id"] for item in chats}
    def add_connection(other, kind):
        if not other or not other.visivel or not request_pair_allowed(me, other):
            return
        item = connections.setdefault(other.pk, {"perfil": chat_profile(other), "nome": other.nome_publico,
                                                   "tipos": [], "conversation_id": active_chats.get(other.pk)})
        if kind not in item["tipos"]:
            item["tipos"].append(kind)
    matches = MatchPerfil.objects.filter(Q(perfil_1=me) | Q(perfil_2=me), status="ATIVO").select_related(
        "perfil_1__pedido", "perfil_1__usuario", "perfil_2__pedido", "perfil_2__usuario")
    for match in matches:
        add_connection(match.perfil_2 if match.perfil_1_id == me.pk else match.perfil_1, "Match")
    signals = AcaoPerfil.objects.filter(Q(usuario=request.user) | Q(perfil=me), tipo__in=["SINAL_FLOR", "SINAL_BEIJINHO", "SINAL_OLA"]).select_related(
        "perfil__pedido", "perfil__usuario", "usuario__perfil_nkata__pedido").order_by("-criado_em")[:100]
    for signal in signals:
        other = signal.perfil if signal.usuario_id == request.user.pk else getattr(signal.usuario, "perfil_nkata", None)
        if other and other.pk != me.pk:
            add_connection(other, "Sinal enviado" if signal.usuario_id == request.user.pk else "Sinal recebido")
    return Response({"conversas": chats, "pedidos": pending, "historico_pedidos": history,
                     "conexoes": list(connections.values())})


def readable_thread(request, conversation_id):
    if not credit_only_enabled():
        return accessible_thread(request, conversation_id)
    me = member(request, require_identity=False)
    chat = get_object_or_404(participants(me), pk=conversation_id)
    other = peer(chat, me)
    if not request_pair_allowed(me, other) or not conversation_has_access(chat):
        raise NotFound("Conversa indisponível.")
    return chat, me, other


def writable_thread(request, conversation_id):
    chat, me, other = readable_thread(request, conversation_id)
    if not pedido_tem_identidade_verificada(me.pedido):
        raise PermissionDenied("Verifique a sua identidade para enviar mensagens.")
    return chat, me, other


def accessible_thread(request, conversation_id):
    me = member(request)
    chat = get_object_or_404(participants(me), pk=conversation_id)
    other = peer(chat, me)
    if not available(me, other) or not conversation_has_access(chat):
        raise NotFound("Conversa indisponível.")
    return chat, me, other


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def close_conversation(request, conversation_id):
    from .models import MatchPerfil
    from .call_api import _active_call_for_match

    me = member(request, require_identity=not credit_only_enabled())
    chat = get_object_or_404(Conversa.objects.filter(Q(perfil_1=me) | Q(perfil_2=me)), pk=conversation_id)
    # Keep lock order compatible with legacy call creation.
    if chat.match_origem_id:
        match = MatchPerfil.objects.select_for_update().get(pk=chat.match_origem_id)
        if _active_call_for_match(match):
            return Response({"detail": "Termine a chamada antes de encerrar a conversa."}, status=409)
    chat = Conversa.objects.select_for_update().get(pk=chat.pk)
    if chat.estado == Conversa.ESTADO_ATIVA:
        chat.estado = Conversa.ESTADO_ENCERRADA
        chat.save(update_fields=["estado"])
        keys = [f"chat-msg:{chat.pk}", f"chat-aceite:{chat.pk}"]
        if chat.match_origem_id:
            keys.append(f"mensagem:{chat.match_origem_id}")
        NotificacaoNKATA.objects.filter(chave__in=keys, destinatario_id__in=[chat.perfil_1.usuario_id, chat.perfil_2.usuario_id]).update(lida=True)
    return Response({"estado": chat.estado})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def typing(request, conversation_id):
    chat, me, _ = writable_thread(request, conversation_id)
    cache.set(f"chat-digitando:{chat.pk}:{me.pk}", True, timeout=5)
    return Response(status=204)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def delete_message(request, conversation_id, message_id):
    chat, _, _ = readable_thread(request, conversation_id)
    thread = chat.match_origem if chat.match_origem_id else chat
    message = get_object_or_404(thread.mensagens.select_for_update(), pk=message_id, remetente=request.user)
    if not message.apagada_em:
        preview = " ".join(message.texto.split())
        if len(preview) > 95:
            preview = f"{preview[:92].rstrip()}…"
        if chat.match_origem_id:
            NotificacaoNKATA.objects.filter(chave=f"mensagem:{chat.match_origem_id}", ator=request.user, texto=preview).delete()
        message.texto = ""
        message.apagada_em = timezone.now()
        message.save(update_fields=["texto", "apagada_em"])
    return Response(status=204)


@transaction.atomic
def send_message(request, chat, me, other, thread):
    # Same lock order as blocking and request decisions; once a block commits,
    # a concurrent native sender cannot write a new message.
    other, _ = lock_pair(me, other.pk, for_send=True)
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    if chat.match_origem_id:
        from .models import MatchPerfil
        MatchPerfil.objects.select_for_update().get(pk=chat.match_origem_id)
    locked = Conversa.objects.select_for_update().get(pk=chat.pk)
    if locked.estado != Conversa.ESTADO_ATIVA or not conversation_has_access(locked):
        raise NotFound("Conversa indisponível.")
    me.refresh_from_db()
    other.refresh_from_db()
    if me.status != "ATIVO" or not pedido_tem_identidade_verificada(me.pedido) or not (request_pair_allowed(me, other) if credit_only_enabled() else available(me, other)):
        raise NotFound("Conversa indisponível.")
    text = request.data.get("texto")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1200:
        raise ValidationError({"detail": "Escreva uma mensagem de até 1200 caracteres."})
    text = text.strip()
    if not can_send_chat_text(request.user, text, thread):
        raise PermissionDenied("Desbloqueie o texto livre para escrever ou responder.")
    reply = request.data.get("resposta_a")
    if reply is not None and not plan_for_user(request.user)["features"]["chat_text"]:
        raise PermissionDenied("Desbloqueie o texto livre para responder a mensagens.")
    if reply is not None and (type(reply) is not int or not 0 < reply < 2**63 or
                              not thread.mensagens.filter(pk=reply, apagada_em__isnull=True).exists()):
        raise ValidationError({"detail": "A mensagem original está indisponível."})
    message = MensagemMatch.objects.create(conversa=chat, match=chat.match_origem, resposta_a_id=reply,
                                           remetente=request.user, texto=text, tipo=chat_message_type(request.user, text))
    if credit_only_enabled() or not chat.match_origem_id:
        notify(other, me, "MENSAGEM", f"chat-msg:{chat.pk}", "Nova mensagem",
               f"{me.nome_publico} enviou-lhe uma mensagem.")
    return Response({"id": message.pk}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_signal(request, conversation_id):
    chat, me, other = writable_thread(request, conversation_id)
    return send_signal(request.user, me, other, request.data.get("tipo", ""), conversation_id=chat.pk, expected_cost=request.data.get("expected_cost"))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def unlock_text(request, conversation_id):
    chat, me, other = writable_thread(request, conversation_id)
    other, _ = lock_pair(me, other.pk, for_send=True)
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    if chat.match_origem_id:
        MatchPerfil.objects.select_for_update().get(pk=chat.match_origem_id)
    get_object_or_404(Conversa.objects.select_for_update(), pk=chat.pk, estado=Conversa.ESTADO_ATIVA)
    try:
        access, charged = unlock_chat(request.user, key=request.data.get("key"), expected_cost=request.data.get("expected_cost"))
    except WalletError as error:
        return Response({"detail": str(error)}, status=409)
    return Response({"charged": charged, "expires_at": access.fim if access else None, "texto_livre": plan_for_user(request.user)["features"]["chat_text"]})


def icebreaker_remaining(user):
    used = MensagemMatch.objects.filter(remetente=user, tipo="QUEBRA_GELO",
                                        criado_em__date=timezone.localdate()).count()
    return max(0, ICEBREAKER_DAILY_LIMIT - used)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def icebreaker(request, conversation_id):
    chat, me, other = writable_thread(request, conversation_id)
    other, _ = lock_pair(me, other.pk, for_send=True)
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    if chat.match_origem_id:
        MatchPerfil.objects.select_for_update().get(pk=chat.match_origem_id)
    chat = get_object_or_404(Conversa.objects.select_for_update(), pk=chat.pk, estado=Conversa.ESTADO_ATIVA)
    code = request.data.get("codigo")
    if not isinstance(code, str) or code not in ICEBREAKERS:
        raise ValidationError({"detail": "Escolha uma pergunta disponível."})
    if icebreaker_remaining(request.user) <= 0:
        return Response({"detail": "Atingiu o limite diário de quebra-gelos."}, status=429)
    if MensagemMatch.objects.filter(conversa=chat, remetente=request.user, tipo="QUEBRA_GELO",
                                    texto=ICEBREAKERS[code], criado_em__date=timezone.localdate()).exists():
        return Response({"detail": "Já enviou esta pergunta hoje nesta conversa."}, status=409)
    message = MensagemMatch.objects.create(conversa=chat, match=chat.match_origem, remetente=request.user,
                                         tipo="QUEBRA_GELO", texto=ICEBREAKERS[code])
    if credit_only_enabled() or not chat.match_origem_id:
        notify(other, me, "MENSAGEM", f"chat-msg:{chat.pk}", "Quebra-gelo",
               f"{me.nome_publico} enviou-lhe uma pergunta.")
    return Response({"id": message.pk, "restantes": icebreaker_remaining(request.user)}, status=201)


MESSAGE_PAGE_SIZE = 50


def cursor_param(request, key):
    value = request.query_params.get(key)
    if value is None:
        return None
    if not value.isascii() or not value.isdecimal() or len(value) > 19 or int(value) >= 2**63:
        raise ValidationError({key: "Cursor inválido."})
    return int(value)


def message_page(request, rows):
    before = cursor_param(request, "antes")
    after = cursor_param(request, "depois")
    loaded_from = cursor_param(request, "estado_desde")
    if before is not None and after is not None:
        raise ValidationError("Utilize apenas um cursor de paginação.")
    if before is not None:
        page = list(rows.filter(pk__lt=before).order_by("-pk")[:MESSAGE_PAGE_SIZE + 1])
        more = len(page) > MESSAGE_PAGE_SIZE
        page = list(reversed(page[:MESSAGE_PAGE_SIZE]))
    elif after is not None:
        page = list(rows.filter(pk__gt=after).order_by("pk")[:MESSAGE_PAGE_SIZE + 1])
        more = len(page) > MESSAGE_PAGE_SIZE
        page = page[:MESSAGE_PAGE_SIZE]
    else:
        page = list(rows.order_by("-pk")[:MESSAGE_PAGE_SIZE + 1])
        more = len(page) > MESSAGE_PAGE_SIZE
        page = list(reversed(page[:MESSAGE_PAGE_SIZE]))
    # Compact state reconciliation also covers older loaded pages. Do not
    # disclose rows outside the authenticated conversation.
    state_rows = rows.filter(pk__gte=loaded_from) if loaded_from is not None else rows.none()
    deleted = list(state_rows.filter(apagada_em__isnull=False).order_by().values_list("pk", flat=True))
    mine = rows.filter(remetente=request.user).order_by("pk")
    first_unread = mine.filter(lida=False).values_list("pk", flat=True).first()
    read = mine.filter(lida=True)
    if first_unread is not None:
        read = read.filter(pk__lt=first_unread)
    read_through = read.order_by("-pk").values_list("pk", flat=True).first() or 0
    return page, {"mais": more, "modo": "depois" if after is not None else "antes" if before is not None else "inicial",
                  "apagadas": deleted, "lidas_ate": read_through}


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def messages(request, conversation_id):
    chat, me, other = (writable_thread if request.method == "POST" else readable_thread)(request, conversation_id)
    thread = chat.match_origem if chat.match_origem_id else chat
    if request.method == "POST":
        return send_message(request, chat, me, other, thread)
    paginated = request.query_params.get("paginado") == "1"
    if paginated:
        # Validate input before marking anything as read.
        before, after = cursor_param(request, "antes"), cursor_param(request, "depois")
        cursor_param(request, "estado_desde")
        if before is not None and after is not None:
            raise ValidationError("Utilize apenas um cursor de paginação.")
    thread.mensagens.filter(lida=False).exclude(remetente=request.user).update(lida=True)
    keys = [f"chat-msg:{chat.pk}", f"chat-aceite:{chat.pk}"]
    if chat.match_origem_id:
        keys.append(f"mensagem:{chat.match_origem_id}")
    NotificacaoNKATA.objects.filter(destinatario=request.user, chave__in=keys, lida=False).update(lida=True)
    rows = thread.mensagens.select_related("remetente__perfil_nkata", "sinal_origem", "nota_voz").order_by("criado_em", "pk")
    page_info = {}
    if paginated:
        rows, page_info = message_page(request, rows)
    can_send = pedido_tem_identidade_verificada(me.pedido)
    features = plan_for_user(request.user)["features"]
    preset = preset_snapshot(request.user) if can_send else {"limite": 0, "restantes": 0, "frases": [], "phrases_en": []}
    offer = chat_credit_snapshot(request.user, features["chat_text"]) if can_send else {"enabled": False, "can_unlock": False}
    return Response({"nome": other.nome_publico, "perfil": chat_profile(other), "match_id": legacy_match_id(chat) if available(me, other) else None,
                     "read_only": not can_send, "identity_required_to_send": not can_send,
                      "consent_state": conversation_consent_state(chat),
                     "a_escrever": bool(cache.get(f"chat-digitando:{chat.pk}:{other.pk}")),
                     "texto_livre": can_send and features["chat_text"], "frases": preset["frases"], "predefinidas": preset,
                     "credito_chat": offer,
                     "credito_voz": voice_credit_offer(request.user, False) if can_send else {"enabled": False},
                     "sinais": _availability_payload(request.user, other) if can_send and other.visivel else {"signals": [], "quota": {}},
                     "quebra_gelo": {"restantes": icebreaker_remaining(request.user) if can_send else 0, "perguntas": [{"codigo": code, "texto": text} for code, text in ICEBREAKERS.items()] if can_send else []},
                     "mensagens": MensagemMatchSerializer(rows, many=True, context={"request": request}).data,
                     **page_info})
