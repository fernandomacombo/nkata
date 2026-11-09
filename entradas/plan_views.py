from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .plan_service import (
    plan_for_user,
    PLAN_PRICES_MZN,
    public_plan_catalog,
    public_recharge_catalog,
    signal_quota_for_user,
)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_plano_da_conta(request):
    plan = plan_for_user(request.user)
    quota = signal_quota_for_user(request.user)

    return Response({
        "current_plan": {
            **plan,
            "price_mzn": PLAN_PRICES_MZN[plan["code"]],
            "price_status": f'{PLAN_PRICES_MZN[plan["code"]]} MT',
            "pricing_status": "proposed",
            "billing_period": None,
        },
        "signal_quota": quota,
        "recharge": {
            "balance": quota["recharge_balance"],
            "packs": public_recharge_catalog(),
        },
        "available_plans": public_plan_catalog(),
        "payments_enabled": False,
        "message": (
            "Os planos já controlam permissões e limites. "
            "Os pagamentos serão ligados numa etapa posterior."
        ),
    })
