from django.urls import path

from . import api_views

app_name = "entradas_api"

urlpatterns = [
    path("status/", api_views.api_status, name="status"),
    path("session/", api_views.api_session, name="session"),
    path("auth/login/", api_views.api_login, name="login"),
    path("auth/logout/", api_views.api_logout, name="logout"),
    path("perfis/", api_views.api_perfis, name="perfis"),
    path("perfis/<int:perfil_id>/", api_views.api_perfil_detalhe, name="perfil_detalhe"),
    path(
        "perfis/<int:perfil_id>/interesse/",
        api_views.api_alternar_interesse,
        name="alternar_interesse",
    ),
    path("minha-conta/", api_views.api_minha_conta, name="minha_conta"),
    path(
        "minha-conta/foto/",
        api_views.api_atualizar_foto_perfil,
        name="atualizar_foto_perfil",
    ),
    path(
        "minha-conta/interesses/",
        api_views.api_meus_interesses,
        name="meus_interesses",
    ),
    path("minha-conta/matches/", api_views.api_meus_matches, name="meus_matches"),
    path(
        "minha-conta/matches/<int:match_id>/conversa/",
        api_views.api_conversa_match,
        name="conversa_match",
    ),
]
