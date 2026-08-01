from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # Páginas Django atuais
    path("", include("entradas.urls")),

    # API preparada para o futuro frontend React + Tailwind
    path("api/", include("entradas.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
