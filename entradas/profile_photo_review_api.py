"""Review queue for registration photos and public profile portraits.

Only staff with the moderation capability may access the queue.
No identity document is ever exposed by these endpoints.
"""
import hashlib

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import PerfilNKATA
from .profile_media_api import _stream
from .user_roles import has_admin_capability


def _allowed(request):
    return request.user.is_active and has_admin_capability(request.user, "content")


def _image_for(profile, slot):
    if slot == 0:
        return profile.pedido.foto_perfil
    if slot not in (1, 2, 3):
        return None
    return getattr(profile.pedido, f"foto_extra_{slot}")


def _state_for(profile, slot):
    if slot == 0:
        return "APROVADO" if profile.foto_destaque_publico_aprovada else profile.foto_destaque_publico_estado
    return getattr(profile.pedido, f"foto_extra_{slot}_estado")


def _record(profile, slot):
    return {
        "profile_id": profile.pk,
        "name": profile.nome_publico,
        "slot": slot,
        "label": "Foto principal (apresentação pública)" if slot == 0 else f"Fotografia {slot + 1}",
        "status": _state_for(profile, slot),
        "version": hashlib.sha256(_image_for(profile, slot).name.encode()).hexdigest(),
        "image_url": f"/api/painel/fotografias/{profile.pk}/{slot}/media/",
    }


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_photo_review_queue(request):
    if not _allowed(request):
        return Response({"detail": "Sem permissão para moderação de fotografias."}, status=403)
    status_filter = str(request.query_params.get("status", "PENDENTE")).upper()
    if status_filter not in ("PENDENTE", "APROVADO", "REJEITADO"):
        return Response({"detail": "Estado inválido."}, status=400)
    profiles = PerfilNKATA.objects.select_related("pedido", "usuario").filter(
        pedido__status="APROVADO", status__in=["ATIVO", "PAUSADO"], usuario__is_staff=False
    ).order_by("-pk")
    rows = []
    # Limit the number of profiles scanned per page; no unbounded table scans.
    for profile in profiles[:200]:
        for slot in range(4):
            if _image_for(profile, slot) and _state_for(profile, slot) == status_filter:
                rows.append(_record(profile, slot))
                if len(rows) >= 100:
                    return Response({"results": rows})
    return Response({"results": rows})


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_photo_review_media(request, profile_id, slot):
    if not _allowed(request):
        return Response({"detail": "Sem permissão."}, status=403)
    profile = PerfilNKATA.objects.select_related("pedido").filter(pk=profile_id).first()
    photo = _image_for(profile, slot) if profile else None
    if not photo:
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    return _stream(photo, private_cache=False) or Response({"detail": "Ficheiro indisponível."}, status=404)


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
@transaction.atomic
def api_review_photo(request, profile_id, slot):
    if not _allowed(request):
        return Response({"detail": "Sem permissão."}, status=403)
    if slot not in (0, 1, 2, 3):
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    action = str(request.data.get("action", "")).strip().lower()
    if action not in ("approve", "reject"):
        return Response({"detail": "Ação inválida."}, status=400)
    profile = PerfilNKATA.objects.select_related("pedido").select_for_update(of=("self",)).filter(
        pk=profile_id, pedido__status="APROVADO", status__in=["ATIVO", "PAUSADO"]
    ).first()
    if not profile or not _image_for(profile, slot):
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    current_version = hashlib.sha256(_image_for(profile, slot).name.encode()).hexdigest()
    if request.data.get("version") != current_version:
        return Response({"detail": "A fotografia foi alterada. Atualize a lista e reveja a nova imagem."}, status=409)
    new_state = "APROVADO" if action == "approve" else "REJEITADO"
    if slot == 0:
        profile.foto_destaque_publico_estado = new_state
        profile.foto_destaque_publico_aprovada = action == "approve"
        if action == "reject":
            profile.destaque_publico = False
        profile.save(update_fields=[
            "foto_destaque_publico_estado", "foto_destaque_publico_aprovada",
            "destaque_publico", "atualizado_em"
        ])
    else:
        pedido = profile.pedido
        flag = f"foto_extra_{slot}_visivel"
        state = f"foto_extra_{slot}_estado"
        setattr(pedido, state, new_state)
        if action == "reject":
            setattr(pedido, flag, False)
        pedido.save(update_fields=[state, flag, "atualizado_em"])
    LogEntry.objects.create(
        user=request.user,
        content_type=ContentType.objects.get_for_model(profile),
        object_id=str(profile.pk),
        object_repr=str(profile)[:200],
        action_flag=CHANGE,
        change_message=f"Moderação da fotografia {slot}: {new_state}",
    )
    return Response({"detail": "Fotografia aprovada." if action == "approve" else "Fotografia rejeitada.", "result": _record(profile, slot)})
