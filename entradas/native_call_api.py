"""Experimental browser call lifecycle; no browser-controlled billing."""
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .media_gateway_api import enabled, reply
from .native_call_service import (
    prepare_call, decide_call, end_call, _locked_session, _allowed, LIVE,
)
from .models import ChamadaConversaCreditoNKATA as Session
from .wallet_service import WalletError, credit_balance, credit_spending_enabled


def gate(request):
    if not enabled():
        return reply({"detail": "Chamadas indisponíveis."}, 404)
    if not request.is_secure():
        return reply({"detail": "Ligação segura necessária."}, 403)
    return None


def serialize(session, user):
    now = timezone.now()
    state = session.estado
    if state in LIVE and session.expira_em <= now:
        state = "EXPIRADA" if state != "ATIVA" else "TERMINADA"
    payer = session.iniciador_id == user.pk
    return {"id": str(session.pk), "conversation_id": session.conversa_id,
            "kind": session.tipo, "state": state, "payer": payer,
            "rate": session.custo_minuto, "max_minutes": session.max_minutos,
            "paid_minutes": session.minutos_pagos, "paid_until": session.pago_ate,
            "expires_at": session.expira_em, "server_time": now,
            "balance": credit_balance(user) if payer else None}


def authorized(session_id, user):
    session, chat, profiles, users = _locked_session(session_id)
    if (user.pk not in (session.iniciador_id, session.destinatario_id)
            or {u.pk for u in users} != {session.iniciador_id, session.destinatario_id}
            or not _allowed(chat, profiles, users)):
        raise WalletError("Chamada indisponível.")
    return session


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def start(request, conversation_id):
    error = gate(request)
    if error is not None:
        return error
    data = request.data
    if not isinstance(data, dict) or set(data) != {"key", "kind", "expected_rate", "max_minutes"}:
        return reply({"detail": "Pedido inválido."}, 400)
    try:
        session = prepare_call(conversation_id, caller_id=request.user.pk,
            key=data["key"], kind=data["kind"], expected_rate=data["expected_rate"],
            max_minutes=data["max_minutes"])
    except WalletError as exc:
        return reply({"detail": str(exc)}, 409)
    return reply(serialize(session, request.user), 201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def current(request):
    error = gate(request)
    if error is not None:
        return error
    sid = Session.objects.filter(
        Q(iniciador_id=request.user.pk) | Q(destinatario_id=request.user.pk),
        estado__in=LIVE, expira_em__gt=timezone.now()
    ).order_by("-criada_em").values_list("pk", flat=True).first()
    if not sid or not credit_spending_enabled():
        return reply({"call": None})
    try:
        session = authorized(sid, request.user)
    except WalletError:
        return reply({"call": None})
    return reply({"call": serialize(session, request.user)})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def detail(request, session_id):
    error = gate(request)
    if error is not None:
        return error
    # Ending remains available to a participant even after blocking or revocation.
    if request.method == "POST" and request.data == {"action": "end"}:
        try:
            session = end_call(session_id, actor_id=request.user.pk)
        except WalletError:
            return reply({"detail": "Chamada indisponível."}, 404)
        return reply({"id": str(session.pk), "state": session.estado})
    try:
        session = authorized(session_id, request.user)
    except WalletError:
        return reply({"detail": "Chamada indisponível."}, 404)
    if request.method == "POST":
        action = request.data.get("action") if isinstance(request.data, dict) else None
        if not isinstance(request.data, dict) or set(request.data) != {"action"} or action not in ("accept", "decline"):
            return reply({"detail": "Pedido inválido."}, 400)
        if request.user.pk != session.destinatario_id:
            return reply({"detail": "Chamada indisponível."}, 404)
        try:
            session = decide_call(session_id, recipient_id=request.user.pk, accept=action == "accept")
        except WalletError:
            return reply({"detail": "Chamada indisponível."}, 404)
    return reply(serialize(session, request.user))
