"""Internal billing contract for a trusted media gateway.

Not a public API. A gateway must authenticate both participants, keep media
blocked until a lease is issued, stop forwarding at its deadline, and stop
immediately on revocation/disconnect. Browser heartbeats are not evidence.
"""
import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .chat_permissions import chat_pair_allowed
from .models import Conversa, PerfilNKATA, ChamadaConversaCreditoNKATA as Session, MovimentoCreditoNKATA, RevisaoMinutoChamadaNKATA as Review
from .call_credit_service import RATES, MAX_AUTHORIZED_MINUTES
from .wallet_service import record_movement, credit_balance, credit_spending_enabled, WalletError

LIVE = ("CHAMANDO","ACEITE","ATIVA")


def _lock_chat(chat_id):
    ids=Conversa.objects.filter(pk=chat_id).values_list("perfil_1_id","perfil_2_id").first()
    if not ids:
        raise WalletError("Conversa indisponível.")
    profiles=list(PerfilNKATA.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    if len(profiles)!=2 or any(not p.usuario_id for p in profiles):
        raise WalletError("Conversa indisponível.")
    users=list(get_user_model().objects.select_for_update().filter(pk__in=[p.usuario_id for p in profiles]).order_by("pk"))
    chat=Conversa.objects.select_for_update().get(pk=chat_id)
    return chat,profiles,users


def _allowed(chat,profiles,users):
    return len(users)==2 and chat.estado==Conversa.ESTADO_ATIVA and chat_pair_allowed(*profiles)


def _locked_session(session_id):
    chat_id=Session.objects.filter(pk=session_id).values_list("conversa_id",flat=True).first()
    if not chat_id:
        raise WalletError("Chamada indisponível.")
    chat,profiles,users=_lock_chat(chat_id)
    session=Session.objects.select_for_update().get(pk=session_id)
    return session,chat,profiles,users


def _end(session,state="TERMINADA"):
    session.estado=state
    session.save(update_fields=["estado"])


@transaction.atomic
def prepare_call(chat_id, *, caller_id, key, kind, expected_rate, max_minutes):
    chat,profiles,users=_lock_chat(chat_id)
    participants={u.pk for u in users}
    if not _allowed(chat,profiles,users) or caller_id not in participants:
        raise WalletError("Conversa indisponível.")
    if not credit_spending_enabled():
        raise WalletError("Chamadas indisponíveis.")
    rate=RATES.get(kind) if isinstance(kind,str) else None
    if rate is None or type(expected_rate) is not int or expected_rate!=rate:
        raise WalletError("Confirme a tarifa atual.")
    if type(max_minutes) is not int or not 1<=max_minutes<=MAX_AUTHORIZED_MINUTES:
        raise WalletError("Limite de minutos inválido.")
    try:
        key=uuid.UUID(str(key))
    except (ValueError,TypeError,AttributeError):
        raise WalletError("Chave inválida.") from None
    old=Session.objects.filter(iniciador_id=caller_id,chave=key).first()
    if old:
        if (old.conversa_id,old.tipo,old.custo_minuto,old.max_minutos)!=(chat_id,kind,rate,max_minutes):
            raise WalletError("Chave já utilizada.")
        return old
    now=timezone.now()
    active=Session.objects.filter(Q(iniciador_id__in=participants)|Q(destinatario_id__in=participants),estado__in=LIVE)
    if active.filter(expira_em__gt=now).exists():
        raise WalletError("Uma das pessoas já está numa chamada.")
    caller=next(u for u in users if u.pk==caller_id)
    if credit_balance(caller)<rate:
        raise WalletError("Saldo insuficiente.")
    return Session.objects.create(conversa=chat,iniciador=caller,destinatario_id=(participants-{caller_id}).pop(),
        chave=key,tipo=kind,custo_minuto=rate,max_minutos=max_minutes,expira_em=now+timedelta(seconds=45))


@transaction.atomic
def decide_call(session_id, *, recipient_id, accept):
    session,chat,profiles,users=_locked_session(session_id)
    if recipient_id!=session.destinatario_id or type(accept) is not bool:
        raise WalletError("Chamada indisponível.")
    if session.estado!="CHAMANDO":
        return session
    if not _allowed(chat,profiles,users) or not credit_spending_enabled() or timezone.now()>=session.expira_em:
        _end(session,"EXPIRADA")
    elif not accept:
        _end(session,"RECUSADA")
    else:
        session.estado="ACEITE"
        session.expira_em=timezone.now()+timedelta(seconds=45)
        session.save(update_fields=["estado","expira_em"])
    return session


@transaction.atomic
def authorize_gateway_minute(session_id, *, connected_user_ids, expected_minute=None):
    """Only called by an authenticated server-side media adapter, never HTTP clients.

    Return the absolute forwarding deadline. No debit before acceptance and
    both verified connections, no late recovery, no retrospective billing.
    """
    session,chat,profiles,users=_locked_session(session_id)
    now=timezone.now()
    if session.estado not in ("ACEITE","ATIVA"):
        return None
    if (not credit_spending_enabled() or not _allowed(chat,profiles,users)
        or {u.pk for u in users}!={session.iniciador_id,session.destinatario_id}
        or set(connected_user_ids)!={session.iniciador_id,session.destinatario_id}):
        _end(session)
        return None
    if expected_minute is not None:
        if type(expected_minute) is not int or expected_minute < 1:
            return None
        if expected_minute == session.minutos_pagos:
            return session.pago_ate if session.pago_ate and now < session.pago_ate else None
        if expected_minute != session.minutos_pagos + 1:
            return None
        if session.pago_ate and now < session.pago_ate:
            return None  # Do not authorize the next minute prematurely.
    if session.pago_ate and now<session.pago_ate:
        return session.pago_ate
    # A renewal may arrive at the boundary; beyond a short grace the
    # connection must be torn down, not charged for the elapsed period.
    if (now>session.expira_em or session.minutos_pagos>=session.max_minutos):
        _end(session)
        return None
    payer=next(u for u in users if u.pk==session.iniciador_id)
    if credit_balance(payer)<session.custo_minuto:
        _end(session)
        return None
    number=session.minutos_pagos+1
    record_movement(payer,key=f"call:native:{session.pk}:minute:{number}",kind="CONSUMO",
        amount=-session.custo_minuto,reference=f"call:{session.pk}",reason=f"Chamada {session.tipo} — minuto {number}")
    session.estado="ATIVA"
    session.minutos_pagos=number
    session.pago_ate=now+timedelta(seconds=60)
    session.expira_em=session.pago_ate+timedelta(seconds=5)
    session.save(update_fields=["estado","minutos_pagos","pago_ate","expira_em"])
    Review.objects.create(chamada=session, minuto=number, prazo=session.pago_ate)
    return session.pago_ate


@transaction.atomic
def end_call(session_id, *, actor_id):
    session,_,_,_=_locked_session(session_id)
    if actor_id not in (session.iniciador_id,session.destinatario_id):
        raise WalletError("Chamada indisponível.")
    if session.estado in LIVE:
        _end(session)
    return session


@transaction.atomic
def reconcile_unstarted_minute(session_id, *, user_ids, minute):
    """Trusted SFU only: no consumer resume was attempted for this minute.

    End the session under the same lock as authorization, even if the debit
    request is still in flight. Never infer non-delivery from a timeout alone.
    """
    session, _, _, users = _locked_session(session_id)
    if (set(user_ids) != {session.iniciador_id, session.destinatario_id}
            or {u.pk for u in users} != set(user_ids)
            or type(minute) is not int or not 1 <= minute <= session.max_minutos):
        raise WalletError("Reconciliação indisponível.")
    payer = next(u for u in users if u.pk == session.iniciador_id)
    key = f"call:native:{session.pk}:minute:{minute}"
    refund_key = f"{key}:refund"
    reference = f"call:{session.pk}"
    debit = MovimentoCreditoNKATA.objects.filter(carteira__usuario=payer, chave=key).first()
    refund = MovimentoCreditoNKATA.objects.filter(carteira__usuario=payer, chave=refund_key).first()
    if refund:
        if (not debit or refund.tipo != "ESTORNO" or refund.quantidade != -debit.quantidade
                or refund.referencia != reference):
            raise WalletError("Reconciliação requer revisão.")
        return {"refunded": refund.quantidade, "state": session.estado}
    if minute not in (session.minutos_pagos, session.minutos_pagos + 1):
        raise WalletError("Minuto não elegível para reconciliação automática.")
    if debit is None and minute != session.minutos_pagos + 1:
        raise WalletError("Débito ausente; requer revisão.")
    if debit and (minute != session.minutos_pagos or debit.tipo != "CONSUMO"
                  or debit.quantidade != -session.custo_minuto or debit.referencia != reference):
        raise WalletError("Débito inconsistente; requer revisão.")
    review = Review.objects.filter(chamada=session, minuto=minute).first()
    if debit and (not review or review.estado != "AUTORIZADO"):
        raise WalletError("Retoma incerta ou iniciada; requer revisão.")
    if session.estado in LIVE:
        _end(session)
    if not debit:
        return {"refunded": 0, "state": session.estado}
    movement = record_movement(payer, key=refund_key, kind="ESTORNO",
        amount=-debit.quantidade, reference=reference,
        reason=f"Estorno de chamada {session.tipo} — minuto {minute} não iniciado")
    review.estado = "ESTORNADO"
    review.save(update_fields=["estado", "atualizada_em"])
    # Keep the original minute index and debit immutable; the session is closed.
    return {"refunded": movement.quantidade, "state": session.estado}


@transaction.atomic
def mark_gateway_resume(session_id, *, user_ids, minute, phase):
    session, chat, profiles, users = _locked_session(session_id)
    if (set(user_ids) != {session.iniciador_id, session.destinatario_id}
            or {u.pk for u in users} != set(user_ids)):
        raise WalletError("Ocorrência indisponível.")
    row = Review.objects.filter(chamada=session, minuto=minute).first()
    if not row:
        raise WalletError("Autorização inexistente.")
    if phase == "INTENT":
        if (session.estado != "ATIVA" or session.minutos_pagos != minute
                or timezone.now() >= row.prazo or not credit_spending_enabled()
                or not _allowed(chat, profiles, users)):
            raise WalletError("Autorização expirada.")
        if row.estado == "RETOMA_INICIADA":
            return row.estado
        if row.estado != "AUTORIZADO":
            raise WalletError("Estado inválido.")
        row.estado = "RETOMA_INICIADA"
    elif phase == "CONFIRMED":
        if row.estado == "CONFIRMADO":
            return row.estado
        if row.estado != "RETOMA_INICIADA":
            raise WalletError("Estado inválido.")
        row.estado = "CONFIRMADO"
    else:
        raise WalletError("Fase inválida.")
    row.save(update_fields=["estado", "atualizada_em"])
    return row.estado
