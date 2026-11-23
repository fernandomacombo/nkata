"""Meta WhatsApp Cloud API callback for verification and test delivery."""

import hmac
import json

from django.conf import settings
from django.http import HttpResponse
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@never_cache
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    verify_token = settings.NKATA_WHATSAPP_VERIFY_TOKEN
    app_secret = settings.NKATA_WHATSAPP_APP_SECRET
    if not (verify_token and app_secret):
        return HttpResponse(status=503)

    if request.method == "GET":
        if request.GET.get("hub.mode") != "subscribe" or not constant_time_compare(
            request.GET.get("hub.verify_token", ""), verify_token,
        ):
            return HttpResponse(status=403)
        challenge = request.GET.get("hub.challenge")
        if not challenge:
            return HttpResponse(status=400)
        return HttpResponse(challenge, content_type="text/plain; charset=utf-8")

    body = request.body
    signature = "sha256=" + hmac.digest(app_secret.encode(), body, "sha256").hex()
    if not constant_time_compare(request.headers.get("X-Hub-Signature-256", ""), signature):
        return HttpResponse(status=403)

    try:
        event = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        return HttpResponse(status=400)
    if not isinstance(event, dict) or event.get("object") != "whatsapp_business_account":
        return HttpResponse(status=400)

    # Test delivery only. No message content is persisted or logged.
    return HttpResponse(status=200)
