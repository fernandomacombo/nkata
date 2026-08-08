from django.conf import settings
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_webrtc_readiness(request):
    stun_urls = list(getattr(settings, "NKATA_WEBRTC_STUN_URLS", []) or [])
    turn_urls = list(getattr(settings, "NKATA_WEBRTC_TURN_URLS", []) or [])
    turn_username = str(getattr(settings, "NKATA_WEBRTC_TURN_USERNAME", "") or "").strip()
    turn_credential = str(getattr(settings, "NKATA_WEBRTC_TURN_CREDENTIAL", "") or "").strip()
    turn_configured = bool(turn_urls and turn_username and turn_credential)

    return Response({
        "stun_configured": bool(stun_urls),
        "turn_configured": turn_configured,
        "mobile_relay_ready": turn_configured,
        "message": (
            "STUN e TURN estão configurados."
            if turn_configured
            else "STUN está disponível, mas TURN ainda não está configurado. Algumas redes móveis ou firewalls podem impedir a chamada."
        ),
    })
