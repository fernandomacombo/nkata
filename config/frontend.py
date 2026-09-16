from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound


def frontend_index(request):
    index_path = Path(settings.BASE_DIR) / "frontend" / "dist" / "index.html"
    try:
        html = index_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HttpResponseNotFound(
            "Frontend não compilado. Execute `npm run build` em frontend/.",
            content_type="text/plain; charset=utf-8",
        )
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    return response
