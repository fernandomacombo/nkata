from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .credit_catalog import credit_catalog
from .payment_service import credit_checkout_enabled
from .user_roles import member_profile_for_user
from .wallet_service import wallet_snapshot


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def wallet(request):
    if not member_profile_for_user(request.user):
        return Response({"detail": "Carteira indisponível."}, status=403)
    response = Response({**wallet_snapshot(request.user), "catalogo": credit_catalog(purchase_enabled=credit_checkout_enabled(request.user))})
    response["Cache-Control"] = "private, no-store"
    return response
