from datetime import timedelta
from functools import partial

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_views import _bloqueio_entre_perfis
from .identity_models import pedido_tem_identidade_verificada
from .models import Conversa, MensagemMatch, PedidoConversa, PerfilNKATA
from .notification_models import NotificacaoNKATA
from .plan_service import CHAT_PHRASES, can_send_chat_text, plan_for_user
from .serializers import MensagemMatchSerializer
from .user_roles import active_member_profile_for_user


def member(request):
    profile = active_member_profile_for_user(request.user)
    if not profile or not pedido_tem_identidade_verificada(profile.pedido):
        raise PermissionDenied("Verifique a sua identidade para usar os chats.")
    return profile


def available(me, other):
    return (other.status == "ATIVO" and other.usuario_id and other.usuario.is_active
            and not other.usuario.is_staff and not other.usuario.is_superuser
            and pedido_tem_identidade_verificada(other.pedido)
            and not _bloqueio_entre_perfis(me, other))


def lock_pair(me, other_id):
    # All mutations acquire the same two rows in the same order, including the
    # first request, when there is no request or conversation row to lock yet.
    profiles = list(PerfilNKATA.objects.select_for_update().filter(
        pk__in=[me.pk, other_id]).order_by("pk"))
    if len(profiles) != 2:
        raise NotFound("Perfil indisponível.")
    other = next(profile for profile in profiles if profile.pk != me.pk)
    if not available(me, other):
        raise NotFound("Perfil indisponível.")
    return other, {"perfil_1": profiles[0], "perfil_2": profiles[1]}


def notify(other, me, kind, key, title, body):
    transaction.on_commit(partial(
        NotificacaoNKATA.objects.update_or_create,
        destinatario_id=other.usuario_id, chave=key,
        defaults=dict(ator_id=me.usuario_id, perfil_id=me.pk, tipo=kind,
                      titulo=title, texto=body, lida=False),
    ), robust=True)


def accept(pending, pair, now):
    chat, _ = Conversa.objects.get_or_create(**pair)
    pending.estado = "ACEITE"
    pending.decidido_em = now
    pending.conversa = chat
    pending.save(update_fields=["estado", "decidido_em", "conversa"])
    notify(pending.remetente, pending.destinatario, "CHAT_ACEITE", f"chat-aceite:{chat.pk}",
           "Pedido de conversa aceite", "Já pode abrir a conversa.")
    return Response({"estado": "ACEITE", "conversation_id": chat.pk})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def send_request(request, profile_id):
    me = member(request)
    other, pair = lock_pair(me, profile_id)
    if not other.visivel:
        raise NotFound("Perfil indisponível.")
    existing = Conversa.objects.filter(**pair).first()
    if existing:
        if existing.match_origem_id and existing.match_origem.status != "ATIVO":
            raise NotFound("Conversa indisponível.")
        return Response({"estado": "ACEITE", "conversation_id": existing.pk})
    requests = PedidoConversa.objects.filter(
        Q(remetente=me, destinatario=other) | Q(remetente=other, destinatario=me))
    now = timezone.now()
    requests.filter(estado="PENDENTE", expira_em__lte=now).update(estado="EXPIRADO")
    pending = requests.filter(estado="PENDENTE").first()
    if pending and pending.destinatario_id == me.pk:
        return accept(pending, pair, now)
    if pending:
        return Response({"id": pending.pk, "estado": pending.estado})
    if requests.filter(remetente=me, estado="RECUSADO", decidido_em__gt=now-timedelta(days=30)).exists():
        return Response({"detail": "Pode voltar a pedir conversa 30 dias após a recusa."}, status=409)
    pending = requests.create(remetente=me, destinatario=other, expira_em=now+timedelta(days=7))
    notify(other, me, "PEDIDO_CHAT", f"pedido-chat:{pending.pk}", "Novo pedido de conversa",
           f"{me.nome_publico} gostaria de conversar consigo.")
    return Response({"id": pending.pk, "estado": pending.estado}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def decide_request(request, request_id):
    me = member(request)
    pending = get_object_or_404(PedidoConversa, pk=request_id, destinatario=me)
    _, pair = lock_pair(me, pending.remetente_id)
    pending.refresh_from_db()
    now = timezone.now()
    decision = request.data.get("decisao")
    if decision not in ("ACEITE", "RECUSADO"):
        raise ValidationError("Decisão inválida.")
    if pending.estado == "PENDENTE" and pending.expira_em <= now:
        pending.estado = "EXPIRADO"
        pending.save(update_fields=["estado"])
    if pending.estado != "PENDENTE":
        return Response({"estado": pending.estado, "conversation_id": pending.conversa_id},
                        status=200 if pending.estado == decision else 409)
    if decision == "ACEITE":
        return accept(pending, pair, now)
    pending.estado = decision
    pending.decidido_em = now
    pending.save(update_fields=["estado", "decidido_em"])
    return Response({"estado": decision})


def participants(me):
    return Conversa.objects.filter(Q(perfil_1=me) | Q(perfil_2=me)).filter(
        Q(match_origem__isnull=True) | Q(match_origem__status="ATIVO")
    ).select_related("perfil_1__pedido", "perfil_2__pedido", "perfil_1__usuario", "perfil_2__usuario")


def peer(chat, me):
    return chat.perfil_2 if chat.perfil_1_id == me.pk else chat.perfil_1


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inbox(request):
    me = member(request)
    chats = []
    for chat in participants(me).order_by("-pk"):
        other = peer(chat, me)
        if available(me, other):
            chats.append({"id": chat.pk, "nome": other.nome_publico, "match_id": chat.match_origem_id})
    requests = PedidoConversa.objects.filter(Q(destinatario=me) | Q(remetente=me),
                                               estado="PENDENTE", expira_em__gt=timezone.now())
    pending = []
    for item in requests.select_related("remetente", "destinatario").order_by("-pk"):
        received = item.destinatario_id == me.pk
        other = item.remetente if received else item.destinatario
        if available(me, other):
            pending.append({"id": item.pk, "recebido": received, "nome": other.nome_publico})
    return Response({"conversas": chats, "pedidos": pending})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def messages(request, conversation_id):
    me = member(request)
    chat = get_object_or_404(participants(me), pk=conversation_id)
    other = peer(chat, me)
    if not available(me, other):
        raise NotFound("Conversa indisponível.")
    thread = chat.match_origem if chat.match_origem_id else chat
    if request.method == "POST":
        text = request.data.get("texto")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 1200:
            raise ValidationError({"detail": "Escreva uma mensagem de até 1200 caracteres."})
        text = text.strip()
        if not can_send_chat_text(request.user, text, thread):
            raise PermissionDenied("Active um pacote com chat para escrever ou responder.")
        reply = request.data.get("resposta_a")
        if reply is not None and (type(reply) is not int or not 0 < reply < 2**63 or
                                  not thread.mensagens.filter(pk=reply, apagada_em__isnull=True).exists()):
            raise ValidationError({"detail": "A mensagem original está indisponível."})
        message = MensagemMatch.objects.create(conversa=chat, match=chat.match_origem, resposta_a_id=reply,
                                               remetente=request.user, texto=text)
        if not chat.match_origem_id:
            notify(other, me, "MENSAGEM", f"chat-msg:{chat.pk}", "Nova mensagem",
                   f"{me.nome_publico} enviou-lhe uma mensagem.")
        return Response({"id": message.pk}, status=201)
    thread.mensagens.filter(lida=False).exclude(remetente=request.user).update(lida=True)
    keys = [f"chat-msg:{chat.pk}", f"chat-aceite:{chat.pk}"]
    if chat.match_origem_id:
        keys.append(f"mensagem:{chat.match_origem_id}")
    NotificacaoNKATA.objects.filter(destinatario=request.user, chave__in=keys).update(lida=True)
    rows = thread.mensagens.select_related("remetente__perfil_nkata").order_by("criado_em", "pk")
    features = plan_for_user(request.user)["features"]
    presets = CHAT_PHRASES[:4] if features.get("chat_presets") and not thread.mensagens.exclude(remetente=request.user).exists() else []
    return Response({"nome": other.nome_publico, "match_id": chat.match_origem_id,
                     "texto_livre": features["chat_text"], "frases": presets,
                     "mensagens": MensagemMatchSerializer(rows, many=True, context={"request": request}).data})
