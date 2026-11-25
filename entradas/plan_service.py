import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from .models import AcaoPerfil, AcessoPlanoNKATA, MensagemMatch


PLAN_GROUP_ESSENCIAL = "NKATA_PLANO_ESSENCIAL"
PLAN_GROUP_PREMIUM = "NKATA_PLANO_PREMIUM"

PLAN_DEFINITIONS = {
    "LIVRE": {
        "code": "LIVRE",
        "label": "NKATA Livre",
        "paid": False,
        "daily_signal_limit": 3,
        "features": {
            "chat_text": False,
            "chat_presets": True,
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
            "advanced_filters": False,
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
            "advanced_filters": False,
            "priority_discovery": False,
        },
    },
}

PLAN_DEFINITIONS["QUINZENAL"] = {
    **PLAN_DEFINITIONS["ESSENCIAL"], "code": "QUINZENAL", "label": "NKATA Quinzenal",
    "features": dict(PLAN_DEFINITIONS["ESSENCIAL"]["features"]),
}
PLAN_DURATIONS = {"LIVRE": 0, "QUINZENAL": 14, "ESSENCIAL": 30, "PREMIUM": 30}
PRESET_DAILY_LIMIT = 5
CHAT_PHRASES_PT = (
    "Olá, tudo bem?",
    "Olá, gostei de conhecer o seu perfil. Como está?",
    "Gostaria de conhecer melhor os seus interesses.",
    "Obrigado pelo seu interesse!",
    "Gostei de conhecer o teu perfil.",
    "Gostaria de continuar esta conversa.",
    "Neste momento não posso conversar.",
)
CHAT_PHRASES_EN = (
    "Hello, how are you?",
    "Hello, I enjoyed reading your profile. How are you?",
    "I would like to learn more about your interests.",
    "Thank you for your interest!",
    "I enjoyed getting to know your profile.",
    "I would like to continue this conversation.",
    "I cannot chat right now.",
)
CHAT_PHRASES = CHAT_PHRASES_PT + CHAT_PHRASES_EN


def preset_remaining(user):
    # Deleted messages retain their type and timestamp; deleting is not a refund.
    used = MensagemMatch.objects.filter(remetente=user, tipo="PREDEFINIDA",
                                       criado_em__date=timezone.localdate()).count()
    return max(0, PRESET_DAILY_LIMIT - used)


def preset_snapshot(user):
    features = plan_for_user(user)["features"]
    remaining = preset_remaining(user) if features.get("chat_presets") and not features["chat_text"] else 0
    return {"limite": PRESET_DAILY_LIMIT, "restantes": remaining,
            "frases": list(CHAT_PHRASES_PT) if remaining else [],
            "phrases_en": list(CHAT_PHRASES_EN) if remaining else []}


def chat_message_type(user, text):
    return "PREDEFINIDA" if text in CHAT_PHRASES and not plan_for_user(user)["features"]["chat_text"] else "TEXTO"


def can_send_chat_text(user, text, match):
    features = plan_for_user(user)["features"]
    if features["chat_text"]:
        return True
    return (
        features.get("chat_presets", False)
        and text in CHAT_PHRASES
        and preset_remaining(user) > 0
    )


RECHARGE_PACKS = {
    10: {"credits": 10, "db_type": "RECARGA_SINAIS_10"},
    30: {"credits": 30, "db_type": "RECARGA_SINAIS_30"},
    80: {"credits": 80, "db_type": "RECARGA_SINAIS_80"},
}
# Keep historical grants readable even when a pack is no longer sold.
PLAN_DURATION_DAYS = 30
PLAN_PRICES_MZN = {"LIVRE": 0, "ESSENCIAL": 250, "PREMIUM": 500, "QUINZENAL": 100}
ACTIVE_RECHARGE_PRICES_MZN = {10: 50}

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

    access = active_plan_access(user)
    return access.plano if access else "LIVRE"


def active_plan_access(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    now = timezone.now()
    return AcessoPlanoNKATA.objects.filter(
        usuario=user, inicio__lte=now, fim__gt=now,
        plano__in=["ESSENCIAL", "PREMIUM", "QUINZENAL"],
    ).exclude(origem="PROMO_CONVERTIDA").first()


def plan_for_user(user):
    access = active_plan_access(user)
    if access and access.origem == "PROMO_LANCAMENTO":
        bonus = PLAN_DEFINITIONS["QUINZENAL"]
        return _with_credit_chat(user, {
            **bonus,
            "label": "Bónus de lançamento",
            "paid": False,
            "features": {
                **bonus["features"],
                "chat_text": False,
                "chat_audio": False,
                "chat_video": False,
                "chat_presets": True,
            },
        })
    definition = PLAN_DEFINITIONS[access.plano if access else "LIVRE"]
    return _with_credit_chat(user, definition)


def _with_credit_chat(user, definition):
    from .wallet_service import active_chat_credit_access
    if getattr(user, "is_authenticated", False) and not definition["features"]["chat_text"] and active_chat_credit_access(user):
        return {**definition, "features": {**definition["features"], "chat_text": True}}
    return definition


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
            "price_mzn": PLAN_PRICES_MZN[definition["code"]],
            "price_status": f'{PLAN_PRICES_MZN[definition["code"]]} MT',
            "pricing_status": "proposed",
            "billing_period": f'{PLAN_DURATIONS[definition["code"]]}_days' if definition["paid"] else None,
            "duration_days": PLAN_DURATIONS[definition["code"]] if definition["paid"] else None,
            "purchase_enabled": False,
        }
        for definition in PLAN_DEFINITIONS.values()
    ]


def public_recharge_catalog():
    return [
        {
            "credits": pack["credits"],
            "price_mzn": ACTIVE_RECHARGE_PRICES_MZN[pack["credits"]],
            "price_status": f'{ACTIVE_RECHARGE_PRICES_MZN[pack["credits"]]} MT',
            "pricing_status": "proposed",
            "purchase_enabled": False,
        }
        for pack in RECHARGE_PACKS.values()
        if pack["credits"] in ACTIVE_RECHARGE_PRICES_MZN
    ]


@transaction.atomic
def assign_plan(user, plan_code):
    """Administrative grant only. A future payment service must verify settlement."""
    plan_code = str(plan_code or "").strip().upper()
    if plan_code not in PLAN_DEFINITIONS:
        raise ValueError("Plano NKATA inválido.")

    get_user_model().objects.select_for_update().get(pk=user.pk)
    now = timezone.now()
    if plan_code == "LIVRE":
        AcessoPlanoNKATA.objects.filter(usuario=user).delete()
    else:
        access = AcessoPlanoNKATA.objects.filter(usuario=user).first()
        # Same-plan renewal preserves unused time; switching starts a fresh term.
        base = access.fim if access and access.plano == plan_code and access.inicio <= now < access.fim else now
        AcessoPlanoNKATA.objects.update_or_create(
            usuario=user,
            defaults={"plano": plan_code, "inicio": now,
                      "fim": base + timedelta(days=PLAN_DURATIONS[plan_code]),
                      "origem": "ADMINISTRATIVA"},
        )
    essencial, premium = ensure_plan_groups()
    user.groups.remove(essencial, premium)
    if plan_code in ("ESSENCIAL", "QUINZENAL"):
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
