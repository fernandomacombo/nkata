from django.conf import settings
from django.http import JsonResponse


class RequestBodySizeLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            raw_length = request.META.get("CONTENT_LENGTH", "")
            try:
                content_length = int(raw_length or 0)
            except (TypeError, ValueError):
                content_length = 0
            limit = int(getattr(settings, "NKATA_MAX_REQUEST_BODY_SIZE", 0) or 0)
            if limit and content_length > limit:
                return JsonResponse(
                    {"detail": "O envio excede o tamanho máximo permitido."},
                    status=413,
                )
        return self.get_response(request)
