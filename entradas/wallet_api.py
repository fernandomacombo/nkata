from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .credit_catalog import credit_catalog
from .user_roles import member_profile_for_user
from .wallet_service import wallet_snapshot


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def wallet(request):
    if not member_profile_for_user(request.user):
        return Response({"detail": "Carteira indisponível."}, status=403)
    return Response({**wallet_snapshot(request.user), "catalogo": credit_catalog()})
