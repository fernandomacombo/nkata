from django.urls import path
from . import api

urlpatterns = [path("pedidos/", api.tickets, name="support_tickets")]
