from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import legacy_redirects, views


app_name = "entradas"

urlpatterns = [
    path("", views.home, name="home"),
    path("entrar/", views.entrar, name="entrar"),
    path("sair/", views.sair, name="sair"),
    path(
        "criar-senha/<uuid:token>/",
        legacy_redirects.criar_senha_moderno,
        name="criar_senha",
    ),
    path("solicitar-entrada/", views.solicitar_entrada, name="solicitar_entrada"),
    path("pedido-recebido/", views.sucesso, name="sucesso"),
    path("minha-conta/", views.minha_conta, name="minha_conta"),
    path("minha-conta/editar/", views.editar_perfil, name="editar_perfil"),
    path(
        "questionario/<uuid:token>/",
        legacy_redirects.questionario_moderno,
        name="responder_questionario",
    ),
    path(
        "questionario-recebido/",
        views.questionario_sucesso,
        name="questionario_sucesso",
    ),
    path("perfis/", views.listar_perfis, name="listar_perfis"),
    path("perfis/<int:perfil_id>/", views.detalhe_perfil, name="detalhe_perfil"),
    path(
        "perfis/<int:perfil_id>/acao/<str:tipo>/",
        views.registrar_acao_perfil,
        name="registrar_acao_perfil",
    ),
    path(
        "perfis/<int:perfil_id>/mensagem/<str:tipo>/",
        views.enviar_mensagem_perfil,
        name="enviar_mensagem_perfil",
    ),
    path(
        "perfis/<int:perfil_id>/interacoes/",
        views.perfil_interacoes,
        name="perfil_interacoes",
    ),
    path(
        "recuperar-senha/",
        legacy_redirects.recuperar_senha_moderno,
        name="password_reset",
    ),
    path(
        "recuperar-senha/enviado/",
        legacy_redirects.recuperar_senha_enviado_moderno,
        name="password_reset_done",
    ),
    path(
        "nova-senha/<uidb64>/<token>/",
        legacy_redirects.nova_senha_moderno,
        name="password_reset_confirm",
    ),
    path(
        "nova-senha/concluido/",
        legacy_redirects.nova_senha_concluida_moderno,
        name="password_reset_complete",
    ),
    path(
        "minha-conta/alternar-visibilidade/",
        views.alternar_visibilidade_perfil,
        name="alternar_visibilidade_perfil",
    ),
    path(
        "minha-conta/alterar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="entradas/password_change_form.html",
            success_url=reverse_lazy("entradas:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "minha-conta/alterar-senha/concluido/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="entradas/password_change_done.html",
        ),
        name="password_change_done",
    ),
    path(
        "perfis/<int:perfil_id>/denunciar/",
        views.denunciar_perfil,
        name="denunciar_perfil",
    ),
    path(
        "minha-conta/matches/<int:match_id>/conversa/",
        views.conversa_match,
        name="conversa_match",
    ),
    path(
        "minha-conta/matches/",
        views.meus_matches,
        name="meus_matches",
    ),
]
