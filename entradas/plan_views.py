from django.conf import settings
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .payment_service import payments_enabled, credit_checkout_enabled
from .wallet_service import wallet_snapshot
from .chat_media_api import voice_credit_offer
from .credit_catalog import credit_catalog
from .user_roles import member_profile_for_user

from .plan_service import (
    plan_for_user,
    PLAN_PRICES_MZN,
    PLAN_DURATIONS,
    active_plan_access,
    public_plan_catalog,
    public_recharge_catalog,
    signal_quota_for_user,
    preset_snapshot,
)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_plano_da_conta(request):
    plan = plan_for_user(request.user)
    quota = signal_quota_for_user(request.user)
    access = active_plan_access(request.user)
    enabled = payments_enabled()
    transition = settings.NKATA_CREDIT_TRANSITION_ENABLED
    legacy_enabled = enabled and not transition

    return Response({
        "current_plan": {
            **plan,
            "is_launch_bonus": bool(access and access.origem == "PROMO_LANCAMENTO"),
            "price_mzn": PLAN_PRICES_MZN[plan["code"]],
            "price_status": f'{PLAN_PRICES_MZN[plan["code"]]} MT',
            "pricing_status": "proposed",
            "billing_period": f'{PLAN_DURATIONS[plan["code"]]}_days' if plan["paid"] else None,
            "duration_days": 15 if access and access.origem == "PROMO_LANCAMENTO" else (
                PLAN_DURATIONS[plan["code"]] if plan["paid"] else None
            ),
            "expires_at": access.fim if access else None,
        },
        "signal_quota": quota,
        "credit_transition": transition,
        "legacy_payments_enabled": legacy_enabled,
        "wallet": {**wallet_snapshot(request.user), "catalogo": credit_catalog(purchase_enabled=credit_checkout_enabled(request.user))} if member_profile_for_user(request.user) else None,
        "chat_presets": preset_snapshot(request.user),
        "voice_credit": voice_credit_offer(request.user, plan["features"].get("chat_audio", False)),
        "recharge": {
            "balance": quota["recharge_balance"],
            "packs": [{**pack, "purchase_enabled": legacy_enabled} for pack in public_recharge_catalog()] if not transition else [],
        },
        "available_plans": [{**item, "purchase_enabled": legacy_enabled and item["paid"]} for item in public_plan_catalog()] if not transition else [],
        "payments_enabled": enabled,
        "message": (
            "Os benefícios são ativados após confirmação do pagamento." if enabled else
            "Os pagamentos ainda não estão disponíveis."
        ),
    })
