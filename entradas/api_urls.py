from django.urls import path

from . import api_views

app_name = "entradas_api"

urlpatterns = [
    path("status/", api_views.api_status, name="status"),
    path("perfis/", api_views.api_perfis, name="perfis"),
    path("perfis/<int:perfil_id>/", api_views.api_perfil_detalhe, name="perfil_detalhe"),
    path("minha-conta/matches/", api_views.api_meus_matches, name="meus_matches"),
]
