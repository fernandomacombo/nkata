from django.urls import path

from . import access_api, api_views, interest_views, notification_views

app_name = "entradas_api"

urlpatterns = [
    path("status/", api_views.api_status, name="status"),
    path("session/", api_views.api_session, name="session"),
    path("auth/login/", api_views.api_login, name="login"),
    path("auth/logout/", api_views.api_logout, name="logout"),
    path("pedir-acesso/", access_api.api_pedir_acesso, name="pedir_acesso"),
    path("perfis/", api_views.api_perfis, name="perfis"),
    path("perfis/<int:perfil_id>/", api_views.api_perfil_detalhe, name="perfil_detalhe"),
    path(
        "perfis/<int:perfil_id>/interesse/",
        interest_views.api_alternar_interesse,
        name="alternar_interesse",
    ),
    path(
        "perfis/<int:perfil_id>/denunciar/",
        api_views.api_denunciar_perfil,
        name="denunciar_perfil",
    ),
    path(
        "perfis/<int:perfil_id>/bloquear/",
        api_views.api_bloquear_perfil,
        name="bloquear_perfil",
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
    path(
        "minha-conta/notificacoes/",
        notification_views.api_notificacoes,
        name="notificacoes",
    ),
    path(
        "minha-conta/notificacoes/marcar-todas-lidas/",
        notification_views.api_marcar_todas_notificacoes_lidas,
        name="marcar_todas_notificacoes_lidas",
    ),
    path(
        "minha-conta/notificacoes/<int:notificacao_id>/ler/",
        notification_views.api_marcar_notificacao_lida,
        name="marcar_notificacao_lida",
    ),
    path(
        "minha-conta/matches/<int:match_id>/notificacoes/lidas/",
        notification_views.api_marcar_notificacoes_match_lidas,
        name="marcar_notificacoes_match_lidas",
    ),
    path("minha-conta/matches/", api_views.api_meus_matches, name="meus_matches"),
    path(
        "minha-conta/matches/<int:match_id>/encerrar/",
        api_views.api_encerrar_match,
        name="encerrar_match",
    ),
    path(
        "minha-conta/matches/<int:match_id>/conversa/",
        api_views.api_conversa_match,
        name="conversa_match",
    ),
]
