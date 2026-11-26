"""Internal minute leases for a future server-controlled media transport.

Intentionally NOT invoked by the current WebRTC API: browser reports alone do
not establish actual media delivery and peer-to-peer transport cannot be cut
off reliably by Django. Only a trusted media adapter may invoke authorization
after verifying both parties' connected media, and it MUST stop transport at
the returned deadline unless a new minute is authorized. No catch-up billing.
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .call_models import ChamadaMatchNKATA
from .chat_permissions import legacy_chat_allowed
from .credit_catalog import AUDIO_CALL_CREDITS_PER_MINUTE, VIDEO_CALL_CREDITS_PER_MINUTE
from .models import MatchPerfil, PerfilNKATA, TarifacaoChamadaNKATA
from .wallet_service import credit_balance, record_movement, WalletError
from .plan_service import plan_for_user

RATES = {"AUDIO": AUDIO_CALL_CREDITS_PER_MINUTE, "VIDEO": VIDEO_CALL_CREDITS_PER_MINUTE}
MAX_AUTHORIZED_MINUTES = 120
RENEWAL_GRACE_SECONDS = 5


def _locked_call(call_id):
    original = ChamadaMatchNKATA.objects.filter(pk=call_id).values("match_id", "iniciador_id").first()
    if not original:
        raise WalletError("Chamada indisponível.")
    pair = MatchPerfil.objects.filter(pk=original["match_id"]).values("perfil_1_id", "perfil_2_id").first()
    if not pair:
        raise WalletError("Conversa indisponível.")
    list(PerfilNKATA.objects.select_for_update().filter(pk__in=list(pair.values())).order_by("pk"))
    payer = get_user_model().objects.select_for_update().get(pk=original["iniciador_id"])
    match = MatchPerfil.objects.select_for_update().get(pk=original["match_id"])
    call = ChamadaMatchNKATA.objects.select_for_update().get(pk=call_id, match=match, iniciador=payer)
    return call, payer, match


@transaction.atomic
def prepare_tariff(call_id, *, payer_id, expected_rate, max_minutes):
    """Record the caller's confirmed maximum cost without debiting anything."""
    call, payer, match = _locked_call(call_id)
    rate = RATES.get(call.tipo)
    if payer.pk != payer_id or not legacy_chat_allowed(payer, match):
        raise WalletError("Chamada indisponível.")
    if type(expected_rate) is not int or expected_rate != rate:
        raise WalletError("Confirme a tarifa atual.")
    if type(max_minutes) is not int or not 1 <= max_minutes <= MAX_AUTHORIZED_MINUTES:
        raise WalletError("Limite de minutos inválido.")
    existing = TarifacaoChamadaNKATA.objects.filter(chamada_id=call.pk).first()
    if existing:
        if (existing.pagador_id, existing.custo_minuto, existing.max_minutos) != (payer_id, rate, max_minutes):
            raise WalletError("A chamada já tem outra autorização.")
        return existing
    if call.estado != ChamadaMatchNKATA.ESTADO_CHAMANDO:
        raise WalletError("A autorização deve preceder a ligação.")
    feature = "chat_video" if call.tipo == "VIDEO" else "chat_audio"
    if plan_for_user(payer)["features"].get(feature):
        raise WalletError("A chamada já está incluída no plano.")
    if credit_balance(payer) < rate:
        raise WalletError("Saldo insuficiente.")
    return TarifacaoChamadaNKATA.objects.create(chamada_id=call.pk, match_id=match.pk, pagador=payer,
        tipo=call.tipo, custo_minuto=rate, max_minutos=max_minutes)


@transaction.atomic
def authorize_media_minute(call_id):
    """Trusted relay only. Return a paid-until deadline or None (stop media).

    A minute is a started 60-second block. Repeated/concurrent requests during
    an already paid block return its original deadline, never another debit.
    An expired, abandoned session cannot be resumed or charged retrospectively.
    """
    call, payer, match = _locked_call(call_id)
    tariff = TarifacaoChamadaNKATA.objects.select_for_update().filter(
        chamada_id=call.pk, pagador=payer, match_id=match.pk, tipo=call.tipo).first()
    if not tariff or tariff.encerrada_em:
        return None
    now = timezone.now()
    if (call.estado != ChamadaMatchNKATA.ESTADO_ATIVA or not call.atendida_em
            or not legacy_chat_allowed(payer, match)):
        if call.estado not in (ChamadaMatchNKATA.ESTADO_CHAMANDO, ChamadaMatchNKATA.ESTADO_CONECTANDO):
            tariff.encerrada_em = now
            tariff.save(update_fields=["encerrada_em"])
        return None
    if tariff.pago_ate and now < tariff.pago_ate:
        return tariff.pago_ate
    late = tariff.pago_ate and now > tariff.pago_ate + timedelta(seconds=RENEWAL_GRACE_SECONDS)
    if late or tariff.minutos_pagos >= tariff.max_minutos or credit_balance(payer) < tariff.custo_minuto:
        tariff.encerrada_em = now
        tariff.save(update_fields=["encerrada_em"])
        return None
    minute = tariff.minutos_pagos + 1
    record_movement(payer, key=f"call:{call.pk}:minute:{minute}", kind="CONSUMO",
        amount=-tariff.custo_minuto, reference=f"call:{call.pk}", reason=f"Chamada {tariff.tipo} — minuto {minute}")
    tariff.minutos_pagos = minute
    tariff.pago_ate = now + timedelta(seconds=60)
    tariff.save(update_fields=["minutos_pagos", "pago_ate"])
    return tariff.pago_ate
