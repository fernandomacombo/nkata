from django.urls import path

from . import (
    access_api,
    account_security_api,
    api_views,
    interest_views,
    moments_api,
    notification_views,
    password_reset_api,
    plan_views,
    profile_api,
    questionnaire_api,
    saved_views,
    signal_views,
)

app_name = "entradas_api"

urlpatterns = [
    path("status/", api_views.api_status, name="status"),
    path("session/", api_views.api_session, name="session"),
    path("auth/login/", api_views.api_login, name="login"),
    path("auth/logout/", api_views.api_logout, name="logout"),
    path(
        "auth/password-change/",
        account_security_api.api_alterar_palavra_passe,
        name="password_change",
    ),
    path(
        "auth/sessions/",
        account_security_api.api_sessoes_da_conta,
        name="account_sessions",
    ),
    path(
        "auth/sessions/terminate-others/",
        account_security_api.api_terminar_outras_sessoes,
        name="terminate_other_sessions",
    ),
    path(
        "auth/password-reset/",
        password_reset_api.api_pedir_recuperacao_senha,
        name="password_reset",
    ),
    path(
        "auth/password-reset/<str:uidb64>/<str:token>/",
        password_reset_api.api_confirmar_recuperacao_senha,
        name="password_reset_confirm",
    ),
    path("pedir-acesso/", access_api.api_pedir_acesso, name="pedir_acesso"),
    path(
        "acompanhar-pedido/",
        access_api.api_acompanhar_pedido,
        name="acompanhar_pedido",
    ),
    path(
        "questionario/<uuid:token>/",
        questionnaire_api.api_questionario,
        name="questionario",
    ),
    path(
        "questionario/<uuid:token>/criar-senha/",
        questionnaire_api.api_criar_senha_questionario,
        name="questionario_criar_senha",
    ),
    path("perfis/", profile_api.api_perfis, name="perfis"),
    path("perfis/<int:perfil_id>/", profile_api.api_perfil_detalhe, name="perfil_detalhe"),
    path(
        "perfis/<int:perfil_id>/interesse/",
        interest_views.api_alternar_interesse,
        name="alternar_interesse",
    ),
    path(
        "perfis/<int:perfil_id>/sinais/",
        signal_views.api_sinais_perfil,
        name="sinais_perfil",
    ),
    path(
        "perfis/<int:perfil_id>/guardar/",
        saved_views.api_alternar_perfil_guardado,
        name="alternar_perfil_guardado",
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
    path("momentos/", moments_api.api_momentos, name="momentos"),
    path(
        "momentos/<int:momento_id>/",
        moments_api.api_apagar_momento,
        name="apagar_momento",
    ),
    path("minha-conta/", api_views.api_minha_conta, name="minha_conta"),
    path(
        "minha-conta/plano/",
        plan_views.api_plano_da_conta,
        name="plano_da_conta",
    ),
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
        "minha-conta/guardados/",
        saved_views.api_perfis_guardados,
        name="perfis_guardados",
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
