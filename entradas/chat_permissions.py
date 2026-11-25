from django.db.models import Q
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission

from .identity_models import pedido_tem_identidade_verificada
from .models import AcaoPerfil, Conversa
from .user_roles import active_member_profile_for_user, member_profile_for_user


IDENTITY_REQUIRED_MESSAGE = "Verifique a sua identidade para abrir conversas no NKATA."


def chat_requires_identity(user):
    profile = member_profile_for_user(user)
    return bool(profile and not pedido_tem_identidade_verificada(profile.pedido))


def request_pair_allowed(a, b):
    """Consent requests require active, unblocked members, not payment or ID."""
    if a.pk == b.pk:
        return False
    for profile in (a, b):
        user = profile.usuario
        if (profile.status != "ATIVO" or not user or not user.is_active
                or user.is_staff or user.is_superuser):
            return False
    return not AcaoPerfil.objects.filter(
        Q(usuario_id=a.usuario_id, perfil_id=b.pk) |
        Q(usuario_id=b.usuario_id, perfil_id=a.pk), tipo="BLOQUEIO"
    ).exists()


def chat_pair_allowed(a, b):
    """Message and media access remains strictly bilateral and verified."""
    return (request_pair_allowed(a, b)
            and pedido_tem_identidade_verificada(a.pedido)
            and pedido_tem_identidade_verificada(b.pedido))


def legacy_chat_allowed(user, match):
    if not match or match.status != "ATIVO":
        return False
    if user.pk not in (match.perfil_1.usuario_id, match.perfil_2.usuario_id):
        return False
    return (Conversa.objects.filter(match_origem=match, estado=Conversa.ESTADO_ATIVA).exists()
            and chat_pair_allowed(match.perfil_1, match.perfil_2))


class ChatIdentityPermission(BasePermission):
    message = IDENTITY_REQUIRED_MESSAGE
    code = "chat_identity_required"

    def has_permission(self, request, view):
        profile = active_member_profile_for_user(request.user)
        if not profile or not pedido_tem_identidade_verificada(profile.pedido):
            return False
        match_id = view.kwargs.get("match_id")
        if match_id:
            chat = Conversa.objects.filter(
                Q(perfil_1=profile) | Q(perfil_2=profile),
                match_origem_id=match_id, estado=Conversa.ESTADO_ATIVA,
                match_origem__status="ATIVO",
            ).select_related("perfil_1__usuario", "perfil_1__pedido",
                             "perfil_2__usuario", "perfil_2__pedido").first()
            if not chat or not chat_pair_allowed(chat.perfil_1, chat.perfil_2):
                raise NotFound("Conversa indisponível.")
        return True
