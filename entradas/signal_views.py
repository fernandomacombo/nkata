import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, Conversa, MatchPerfil, MensagemMatch, PerfilNKATA
from .chat_permissions import chat_pair_allowed
from .credit_catalog import SIGNAL_DEFINITIONS, SIGNAL_CHAT_TEXT
from .plan_service import (
    PLAN_DEFINITIONS,
    PLAN_SIGNAL_PREFIX,
    RECHARGE_SIGNAL_PREFIX,
    signal_quota_for_user,
)
from .user_roles import active_member_profile_for_user


User = get_user_model()
FREE_DAILY_SIGNAL_LIMIT = PLAN_DEFINITIONS["LIVRE"]["daily_signal_limit"]
SIGNAL_DB_TYPES = [item["db_type"] for item in SIGNAL_DEFINITIONS.values()]


def _perfil_do_utilizador(user):
    return active_member_profile_for_user(user)


def _bloqueio_entre_perfis(perfil_a, perfil_b):
    conditions = Q()
    if perfil_a.usuario_id:
        conditions |= Q(
            usuario_id=perfil_a.usuario_id,
            perfil_id=perfil_b.id,
            tipo="BLOQUEIO",
        )
    if perfil_b.usuario_id:
        conditions |= Q(
            usuario_id=perfil_b.usuario_id,
            perfil_id=perfil_a.id,
            tipo="BLOQUEIO",
        )
    return bool(conditions) and AcaoPerfil.objects.filter(conditions).exists()


def build_signal_quota(used, limit=FREE_DAILY_SIGNAL_LIMIT):
    """Compatibilidade com os testes antigos da regra do plano Livre."""
    used = max(0, int(used or 0))
    limit = max(0, int(limit or 0))
    return {
        "plan": "LIVRE",
        "daily_limit": limit,
        "used_today": min(used, limit),
        "remaining_today": max(0, limit - used),
        "limit_reached": used >= limit,
    }


def _signals_today(user):
    today = timezone.localdate()
    return AcaoPerfil.objects.filter(
        usuario=user,
        tipo__in=SIGNAL_DB_TYPES,
        criado_em__date=today,
    )


def _signal_payload(item):
    return {
        "type": item["db_type"].removeprefix("SINAL_"),
        "label": item["label"],
        "icon": item["icon"],
        "message": item["message"],
    }


def _availability_payload(user, perfil_alvo):
    today_qs = _signals_today(user)
    sent_types = set(
        today_qs.filter(perfil=perfil_alvo).values_list("tipo", flat=True)
    )
    signals = []
    for item in SIGNAL_DEFINITIONS.values():
        payload = _signal_payload(item)
        payload["sent_to_profile_today"] = item["db_type"] in sent_types
        signals.append(payload)
    return {
        "quota": signal_quota_for_user(user, sent_today=today_qs.count()),
        "signals": signals,
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_sinais_perfil(request, perfil_id):
    try:
        perfil_alvo = PerfilNKATA.objects.select_related("usuario").get(
            id=perfil_id,
            status="ATIVO",
            visivel=True,
        )
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    perfil_atual = _perfil_do_utilizador(request.user)
    if not perfil_atual or perfil_atual.status != "ATIVO":
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )

    if perfil_atual.id == perfil_alvo.id:
        return Response(
            {"detail": "Não pode enviar um sinal para o seu próprio perfil."},
            status=403,
        )

    if _bloqueio_entre_perfis(perfil_atual, perfil_alvo):
        return Response({"detail": "Esta interação não está disponível."}, status=403)

    if request.method == "GET":
        return Response(_availability_payload(request.user, perfil_alvo))

    return send_signal(request.user, perfil_atual, perfil_alvo, request.data.get("tipo", ""))


def send_signal(user, perfil_atual, perfil_alvo, raw_type, conversation_id=None):
    raw_type = str(raw_type).strip().upper()
    definition = SIGNAL_DEFINITIONS.get(raw_type)
    if not definition:
        return Response(
            {"detail": "Escolha um sinal disponível no NKATA."},
            status=400,
        )

    with transaction.atomic():
        # Serializa envios concorrentes da mesma conta em bases que suportam
        # row locking. Em SQLite a escrita continua protegida pela transação.
        profiles = list(PerfilNKATA.objects.select_for_update().filter(pk__in=[perfil_atual.pk, perfil_alvo.pk]).order_by("pk"))
        if len(profiles) != 2:
            return Response({"detail": "Perfil indisponível."}, status=404)
        perfil_atual = next(p for p in profiles if p.pk == perfil_atual.pk)
        perfil_alvo = next(p for p in profiles if p.pk != perfil_atual.pk)
        if perfil_atual.status != "ATIVO" or perfil_alvo.status != "ATIVO" or not perfil_alvo.visivel or _bloqueio_entre_perfis(perfil_atual, perfil_alvo):
            return Response({"detail": "Esta interação não está disponível."}, status=403)
        User.objects.select_for_update().get(pk=user.pk)
        chat = None
        if chat_pair_allowed(perfil_atual, perfil_alvo):
            candidate = Conversa.objects.filter(perfil_1=profiles[0], perfil_2=profiles[1], estado=Conversa.ESTADO_ATIVA).first()
            if candidate:
                if candidate.match_origem_id:
                    MatchPerfil.objects.select_for_update().get(pk=candidate.match_origem_id)
                chat = Conversa.objects.select_for_update().filter(pk=candidate.pk, estado=Conversa.ESTADO_ATIVA).first()
        if conversation_id is not None and (not chat or chat.pk != conversation_id):
            return Response({"detail": "Conversa indisponível."}, status=404)

        today_qs = _signals_today(user)
        already_sent = today_qs.filter(
            perfil=perfil_alvo,
            tipo=definition["db_type"],
        ).exists()
        if already_sent:
            return Response(
                {
                    "detail": f"Já enviou {definition['label']} para este perfil hoje.",
                    "code": "signal_already_sent_today",
                    **_availability_payload(user, perfil_alvo),
                },
                status=409,
            )

        quota = signal_quota_for_user(user, sent_today=today_qs.count())
        source = quota.get("next_source")
        if not source:
            return Response(
                {
                    "detail": (
                        f"Usou os {quota['daily_limit']} sinais disponíveis hoje no "
                        f"{quota['plan_label']} e não tem saldo de recarga."
                    ),
                    "code": "signal_allowance_exhausted",
                    "quota": quota,
                },
                status=429,
            )

        prefix = PLAN_SIGNAL_PREFIX if source == "PLAN" else RECHARGE_SIGNAL_PREFIX
        action = AcaoPerfil.objects.create(
            perfil=perfil_alvo,
            usuario=user,
            tipo=definition["db_type"],
            session_key=(
                f"{prefix}{user.pk}:{timezone.localdate():%Y%m%d}:"
                f"{uuid.uuid4().hex[:16]}"
            ),
        )
        if chat:
            MensagemMatch.objects.create(conversa=chat, match=chat.match_origem, remetente=user,
                tipo="SINAL", sinal_origem=action, texto=SIGNAL_CHAT_TEXT[raw_type])

    payload = _availability_payload(user, perfil_alvo)
    return Response(
        {
            "ok": True,
            "signal": _signal_payload(definition),
            "source": source,
            "message": f"{definition['label']} enviado para {perfil_alvo.nome_publico}.",
            **payload,
        },
        status=201,
    )
