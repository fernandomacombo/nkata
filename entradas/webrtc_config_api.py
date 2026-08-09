from django.conf import settings
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .webrtc_credentials import turn_is_configured


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_webrtc_readiness(request):
    stun_urls = list(getattr(settings, "NKATA_WEBRTC_STUN_URLS", []) or [])
    turn_configured = turn_is_configured()

    return Response({
        "stun_configured": bool(stun_urls),
        "turn_configured": turn_configured,
        "mobile_relay_ready": turn_configured,
        # Estado técnico apenas. A ausência de TURN não deve ser apresentada
        # automaticamente como erro ao membro dentro da conversa.
        "message": "STUN e TURN estão configurados." if turn_configured else "",
    })
