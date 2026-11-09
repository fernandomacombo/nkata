from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .payment_service import payments_enabled

from .plan_service import (
    plan_for_user,
    PLAN_PRICES_MZN,
    PLAN_DURATION_DAYS,
    active_plan_access,
    public_plan_catalog,
    public_recharge_catalog,
    signal_quota_for_user,
)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_plano_da_conta(request):
    plan = plan_for_user(request.user)
    quota = signal_quota_for_user(request.user)
    access = active_plan_access(request.user)
    enabled = payments_enabled()

    return Response({
        "current_plan": {
            **plan,
            "price_mzn": PLAN_PRICES_MZN[plan["code"]],
            "price_status": f'{PLAN_PRICES_MZN[plan["code"]]} MT',
            "pricing_status": "proposed",
            "billing_period": "30_days" if plan["paid"] else None,
            "duration_days": PLAN_DURATION_DAYS if plan["paid"] else None,
            "expires_at": access.fim if access else None,
        },
        "signal_quota": quota,
        "recharge": {
            "balance": quota["recharge_balance"],
            "packs": [{**pack, "purchase_enabled": enabled} for pack in public_recharge_catalog()],
        },
        "available_plans": [{**item, "purchase_enabled": enabled and item["paid"]} for item in public_plan_catalog()],
        "payments_enabled": enabled,
        "message": (
            "Os benefícios são ativados após confirmação do pagamento." if enabled else
            "Os pagamentos ainda não estão disponíveis."
        ),
    })
