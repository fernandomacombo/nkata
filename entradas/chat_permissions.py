from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission

from .identity_models import pedido_tem_identidade_verificada
from .models import Conversa
from .user_roles import member_profile_for_user


IDENTITY_REQUIRED_MESSAGE = "Verifique a sua identidade para abrir conversas no NKATA."


def chat_requires_identity(user):
    profile = member_profile_for_user(user)
    return bool(profile and not pedido_tem_identidade_verificada(profile.pedido))


class ChatIdentityPermission(BasePermission):
    message = IDENTITY_REQUIRED_MESSAGE
    code = "chat_identity_required"

    def has_permission(self, request, view):
        if chat_requires_identity(request.user):
            return False
        match_id = view.kwargs.get("match_id")
        if match_id and not Conversa.objects.filter(match_origem_id=match_id, estado=Conversa.ESTADO_ATIVA).exists():
            raise NotFound("Conversa indisponível.")
        return True
