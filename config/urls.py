from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from entradas.discovery_api import shared_question
from .frontend import frontend_index
from .social_preview import social_preview

urlpatterns = [
    path("pergunta-do-dia/<str:day>/", shared_question, name="shared-question"),
    path("admin/", admin.site.urls),
    path("social-preview.png", social_preview, name="nkata-social-preview"),
    path("api/", include("entradas.api_urls")),
    path("api/ajuda/", include("helpdesk.urls")),
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
