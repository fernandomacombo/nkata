from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .user_roles import (
    ADMIN_CAPABILITIES,
    admin_capability_codes,
    set_admin_capabilities,
)


def _staff_payload(user):
    return {
        "id": user.id,
        "name": user.get_full_name() or user.get_username(),
        "email": user.email,
        "active": user.is_active,
        "capabilities": admin_capability_codes(user),
    }


def _superuser_only(request):
    return bool(request.user.is_authenticated and request.user.is_superuser)


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAdminUser])
@transaction.atomic
def api_admin_staff(request):
    if not _superuser_only(request):
        return Response({"detail": "Apenas o superutilizador pode gerir a equipa."}, status=403)

    User = get_user_model()
    if request.method == "GET":
        users = User.objects.filter(is_staff=True, is_superuser=False).order_by("email", "username")
        return Response({
            "capabilities": list(ADMIN_CAPABILITIES),
            "results": [_staff_payload(user) for user in users],
        })

    email = str(request.data.get("email", "")).strip().lower()
    name = " ".join(str(request.data.get("name", "")).split())
    password = str(request.data.get("password", ""))
    if "@" not in email:
        return Response({"email": ["Introduza um email válido."]}, status=400)
    if len(password) < 10:
        return Response({"password": ["Use pelo menos 10 caracteres."]}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return Response({"email": ["Já existe uma conta com este email."]}, status=400)

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_staff=True,
        is_active=True,
    )
    if name:
        parts = name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.save(update_fields=["first_name", "last_name"])
    set_admin_capabilities(user, request.data.get("capabilities", []))
    return Response({"message": "Operador criado.", "staff": _staff_payload(user)}, status=201)


@api_view(["PATCH"])
@permission_classes([permissions.IsAdminUser])
@transaction.atomic
def api_admin_staff_detail(request, staff_id):
    if not _superuser_only(request):
        return Response({"detail": "Apenas o superutilizador pode gerir a equipa."}, status=403)

    User = get_user_model()
    user = User.objects.filter(id=staff_id, is_staff=True, is_superuser=False).first()
    if not user:
        return Response({"detail": "Operador não encontrado."}, status=404)

    if "active" in request.data:
        user.is_active = bool(request.data.get("active"))
        user.save(update_fields=["is_active"])
    if "capabilities" in request.data:
        try:
            set_admin_capabilities(user, request.data.get("capabilities", []))
        except ValueError as error:
            return Response({"detail": str(error)}, status=400)
    return Response({"message": "Permissões atualizadas.", "staff": _staff_payload(user)})
