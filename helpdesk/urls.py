from django.urls import path
from . import api

urlpatterns = [
    path("pedidos/", api.tickets, name="support_tickets"),
    path("painel/pedidos/", api.admin_tickets, name="admin_support_tickets"),
    path("painel/pedidos/<uuid:ticket_id>/responder/", api.admin_reply, name="admin_support_reply"),
]
