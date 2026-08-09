from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from .frontend import frontend_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("entradas.api_urls")),
]

if settings.DEBUG:
    # O frontend Vite roda separadamente em desenvolvimento; estas páginas
    # permanecem apenas como compatibilidade local.
    urlpatterns += [path("", include("entradas.urls"))]
else:
    # Em produção, todas as rotas da aplicação são resolvidas pelo React.
    urlpatterns += [
        re_path(
            r"^(?!api/|admin/|static/|assets/|media/).*$",
            frontend_index,
        )
    ]
