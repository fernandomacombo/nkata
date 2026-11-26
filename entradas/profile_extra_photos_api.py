"""Owner-controlled extra photographs from registration.

These are profile photos, never identity documents. Publication requires owner authorization and moderation.
"""
from pathlib import PurePath
from uuid import uuid4

from PIL import Image, UnidentifiedImageError
from django.db import transaction
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .api_views import _validar_foto_perfil
from .media_validation import sanitized_image_upload
from .models import PerfilNKATA
from .profile_media_api import _blocked, _stream
from .user_roles import active_member_profile_for_user, member_profile_for_user


def _fields(slot):
    if slot not in (1, 2, 3):
        return None
    return f"foto_extra_{slot}", f"foto_extra_{slot}_visivel"


def _own_profile(user):
    return member_profile_for_user(user)


def _owner_payload(profile):
    pedido = profile.pedido
    entries = []
    for slot in (1, 2, 3):
        image_field, flag_field = _fields(slot)
        image = getattr(pedido, image_field)
        entries.append({
            "slot": slot,
            "rejection_reason": getattr(pedido, f"foto_extra_{slot}_motivo"),
            "review_status": getattr(pedido, f"foto_extra_{slot}_estado"),
            "exists": bool(image),
            "visible": bool(image and getattr(pedido, flag_field) and getattr(pedido, f"foto_extra_{slot}_estado") == "APROVADO"),
            "publication_authorized": bool(image and getattr(pedido, flag_field)),
            "media_url": (
                f"/api/perfis/{profile.pk}/fotografias/{slot}/" if image else None
            ),
        })
    return {"results": entries}


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_my_extra_photos(request):
    profile = _own_profile(request.user)
    if not profile:
        return Response({"detail": "Perfil não encontrado."}, status=404)
    return Response(_owner_payload(profile))


@api_view(["POST", "PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def api_manage_extra_photo(request, slot):
    fields = _fields(slot)
    profile = _own_profile(request.user)
    if not fields or not profile:
        return Response({"detail": "Fotografia não encontrada."}, status=404)

    profile = PerfilNKATA.objects.select_for_update().get(pk=profile.pk)
    image_field, flag_field = fields
    pedido = profile.pedido
    current = getattr(pedido, image_field)

    if request.method == "PATCH":
        if not current:
            return Response({"detail": "Adicione uma fotografia primeiro."}, status=400)
        if type(request.data.get("visible")) is not bool:
            return Response({"visible": ["Selecione mostrar ou ocultar."]}, status=400)
        visible = request.data["visible"]
        if visible and getattr(pedido, f"foto_extra_{slot}_estado") != "APROVADO":
            return Response({"detail": "A fotografia necessita de aprovação da moderação."}, status=400)
        if visible and (
            profile.status != "ATIVO" or not profile.visivel
            or pedido.status != "APROVADO"
        ):
            return Response({"detail": "Ative o perfil e conclua a aprovação da conta antes de mostrar fotografias."}, status=400)
        setattr(pedido, flag_field, visible)
        pedido.save(update_fields=[flag_field, "atualizado_em"])
        return Response(_owner_payload(profile))

    if request.method == "POST":
        upload = request.FILES.get("foto")
        error = _validar_foto_perfil(upload)
        if error:
            return Response({"foto": [error]}, status=400)
        try:
            image = sanitized_image_upload(upload)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
            return Response({"foto": ["Não foi possível preparar esta fotografia."]}, status=400)
        image.name = f"{uuid4().hex}{PurePath(image.name).suffix}"
        old_file = current
        setattr(pedido, image_field, image)
        setattr(pedido, flag_field, request.data.get("publicar_fotos_perfil") == "on")
        setattr(pedido, f"foto_extra_{slot}_estado", "PENDENTE")
        setattr(pedido, f"foto_extra_{slot}_motivo", "")
        pedido.save(update_fields=[image_field, flag_field, f"foto_extra_{slot}_estado", f"foto_extra_{slot}_motivo", "atualizado_em"])
        if old_file and old_file.name != getattr(pedido, image_field).name:
            # A fotografia anterior é substituída apenas depois do registo guardado.
            transaction.on_commit(lambda: old_file.delete(save=False), robust=True)
        return Response(_owner_payload(profile))

    # DELETE is explicit. It removes only this extra photo, never profile,
    # identity evidence or the main profile picture.
    old_file = current
    setattr(pedido, image_field, "")
    setattr(pedido, flag_field, False)
    setattr(pedido, f"foto_extra_{slot}_estado", "PENDENTE")
    setattr(pedido, f"foto_extra_{slot}_motivo", "")
    pedido.save(update_fields=[image_field, flag_field, f"foto_extra_{slot}_estado", f"foto_extra_{slot}_motivo", "atualizado_em"])
    if old_file:
        transaction.on_commit(lambda: old_file.delete(save=False), robust=True)
    return Response(_owner_payload(profile))


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_extra_photo_media(request, profile_id, slot):
    fields = _fields(slot)
    if not fields:
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    profile = (
        PerfilNKATA.objects.select_related("pedido", "usuario")
        .filter(pk=profile_id).first()
    )
    if not profile:
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    field_name, flag_name = fields
    owner = profile.usuario_id == request.user.pk
    if not owner:
        viewer = active_member_profile_for_user(request.user)
        if not (
            viewer
            and profile.status == "ATIVO"
            and profile.visivel
            and profile.pedido.status == "APROVADO"
            and profile.usuario
            and profile.usuario.is_active
            and not _blocked(viewer, profile)
            and getattr(profile.pedido, flag_name)
            and getattr(profile.pedido, f"foto_extra_{slot}_estado") == "APROVADO"
        ):
            return Response({"detail": "Fotografia não encontrada."}, status=404)
    image = getattr(profile.pedido, field_name)
    if not image:
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    response = _stream(image, private_cache=False)
    return response or Response({"detail": "Fotografia não encontrada."}, status=404)
