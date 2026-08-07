import uuid

from django.contrib.auth.models import Group
from django.utils import timezone

from .models import AcaoPerfil


PLAN_GROUP_ESSENCIAL = "NKATA_PLANO_ESSENCIAL"
PLAN_GROUP_PREMIUM = "NKATA_PLANO_PREMIUM"

PLAN_DEFINITIONS = {
    "LIVRE": {
        "code": "LIVRE",
        "label": "NKATA Livre",
        "paid": False,
        "daily_signal_limit": 3,
        "features": {
            "chat_text": True,
            "chat_audio": False,
            "chat_video": False,
            "status_text": True,
            "status_media": False,
            "feed_view": True,
            "feed_media_publish": False,
            "advanced_filters": False,
            "priority_discovery": False,
        },
    },
    "ESSENCIAL": {
        "code": "ESSENCIAL",
        "label": "NKATA Essencial",
        "paid": True,
        "daily_signal_limit": 15,
        "features": {
            "chat_text": True,
            "chat_audio": True,
            "chat_video": True,
            "status_text": True,
            "status_media": True,
            "feed_view": True,
            "feed_media_publish": True,
            "advanced_filters": True,
            "priority_discovery": False,
        },
    },
    "PREMIUM": {
        "code": "PREMIUM",
        "label": "NKATA Premium",
        "paid": True,
        "daily_signal_limit": 40,
        "features": {
            "chat_text": True,
            "chat_audio": True,
            "chat_video": True,
            "status_text": True,
            "status_media": True,
            "feed_view": True,
            "feed_media_publish": True,
            "advanced_filters": True,
            "priority_discovery": True,
        },
    },
}

RECHARGE_PACKS = {
    10: {"credits": 10, "db_type": "RECARGA_SINAIS_10"},
    30: {"credits": 30, "db_type": "RECARGA_SINAIS_30"},
    80: {"credits": 80, "db_type": "RECARGA_SINAIS_80"},
}
RECHARGE_TYPE_CREDITS = {
    pack["db_type"]: pack["credits"] for pack in RECHARGE_PACKS.values()
}
PLAN_SIGNAL_PREFIX = "sinal:plano:"
RECHARGE_SIGNAL_PREFIX = "sinal:recarga:"


def ensure_plan_groups():
    essencial, _ = Group.objects.get_or_create(name=PLAN_GROUP_ESSENCIAL)
    premium, _ = Group.objects.get_or_create(name=PLAN_GROUP_PREMIUM)
    return essencial, premium


def plan_code_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return "LIVRE"

    group_names = set(
        user.groups.filter(
            name__in=[PLAN_GROUP_ESSENCIAL, PLAN_GROUP_PREMIUM]
        ).values_list("name", flat=True)
    )
    if PLAN_GROUP_PREMIUM in group_names:
        return "PREMIUM"
    if PLAN_GROUP_ESSENCIAL in group_names:
        return "ESSENCIAL"
    return "LIVRE"


def plan_for_user(user):
    return PLAN_DEFINITIONS[plan_code_for_user(user)]


def signal_actions_for_user(user):
    return AcaoPerfil.objects.filter(usuario=user, tipo__startswith="SINAL_")


def signals_sent_today(user):
    return signal_actions_for_user(user).filter(
        criado_em__date=timezone.localdate()
    ).count()


def recharge_balance_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return 0

    grant_types = list(
        AcaoPerfil.objects.filter(
            usuario=user,
            tipo__in=RECHARGE_TYPE_CREDITS,
        ).values_list("tipo", flat=True)
    )
    granted = sum(RECHARGE_TYPE_CREDITS.get(item, 0) for item in grant_types)
    consumed = signal_actions_for_user(user).filter(
        session_key__startswith=RECHARGE_SIGNAL_PREFIX
    ).count()
    return max(0, granted - consumed)


def build_quota_snapshot(plan_code, sent_today=0, recharge_balance=0):
    plan = PLAN_DEFINITIONS.get(plan_code, PLAN_DEFINITIONS["LIVRE"])
    sent_today = max(0, int(sent_today or 0))
    recharge_balance = max(0, int(recharge_balance or 0))
    daily_limit = int(plan["daily_signal_limit"])
    plan_used = min(sent_today, daily_limit)
    plan_remaining = max(0, daily_limit - sent_today)

    return {
        "plan": plan["code"],
        "plan_label": plan["label"],
        "daily_limit": daily_limit,
        "used_today": plan_used,
        "sent_today": sent_today,
        "remaining_today": plan_remaining,
        "recharge_balance": recharge_balance,
        "limit_reached": plan_remaining <= 0 and recharge_balance <= 0,
        "next_source": (
            "PLAN"
            if plan_remaining > 0
            else "RECHARGE"
            if recharge_balance > 0
            else None
        ),
    }


def signal_quota_for_user(user, sent_today=None):
    if sent_today is None:
        sent_today = signals_sent_today(user)
    return build_quota_snapshot(
        plan_code_for_user(user),
        sent_today=sent_today,
        recharge_balance=recharge_balance_for_user(user),
    )


def public_plan_catalog():
    return [
        {
            **definition,
            "price_mzn": None,
            "price_status": "A definir",
            "purchase_enabled": False,
        }
        for definition in PLAN_DEFINITIONS.values()
    ]


def public_recharge_catalog():
    return [
        {
            "credits": pack["credits"],
            "price_mzn": None,
            "price_status": "A definir",
            "purchase_enabled": False,
        }
        for pack in RECHARGE_PACKS.values()
    ]


def assign_plan(user, plan_code):
    plan_code = str(plan_code or "").strip().upper()
    if plan_code not in PLAN_DEFINITIONS:
        raise ValueError("Plano NKATA inválido.")

    essencial, premium = ensure_plan_groups()
    user.groups.remove(essencial, premium)
    if plan_code == "ESSENCIAL":
        user.groups.add(essencial)
    elif plan_code == "PREMIUM":
        user.groups.add(premium)
    return PLAN_DEFINITIONS[plan_code]


def grant_recharge(user, credits):
    credits = int(credits)
    pack = RECHARGE_PACKS.get(credits)
    if not pack:
        raise ValueError("Recarga NKATA inválida.")

    perfil = getattr(user, "perfil_nkata", None)
    if not perfil:
        raise ValueError("Esta conta ainda não tem perfil NKATA.")

    return AcaoPerfil.objects.create(
        perfil=perfil,
        usuario=user,
        tipo=pack["db_type"],
        session_key=f"recarga:{credits}:{user.pk}:{uuid.uuid4().hex[:20]}",
    )
