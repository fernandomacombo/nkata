import mimetypes
import os

from django.db.models import Q
from django.http import FileResponse
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, PedidoEntrada, PerfilNKATA
from .identity_models import VerificacaoIdentidadeNKATA


ADMIN_MEDIA_FIELDS = {
    "foto_perfil",
    "foto_extra_1",
    "foto_extra_2",
    "foto_extra_3",
    "bi_frente",
    "bi_verso",
    "selfie_com_bi",
}

NKATA_ID_MEDIA_FIELDS = {
    "bi_frente",
    "bi_verso",
    "selfie_ao_vivo",
    "selfie_desafio",
}


def profile_photo_url(perfil):
    if not perfil or not perfil.foto_principal:
        return None
    version = getattr(perfil.pedido, "atualizado_em", None)
    stamp = int(version.timestamp()) if version else 0
    return f"/api/perfis/{perfil.id}/foto/?v={stamp}"


def _stream(field_file, *, private_cache=True):
    try:
        handle = field_file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        return None

    content_type = mimetypes.guess_type(field_file.name)[0] or "application/octet-stream"
    response = FileResponse(handle, content_type=content_type)
    response["Content-Disposition"] = (
        f'inline; filename="{os.path.basename(field_file.name)}"'
    )
    response["Cache-Control"] = "private, max-age=300" if private_cache else "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response


def _blocked(perfil_atual, perfil_alvo):
    if not perfil_atual:
        return False
    conditions = Q()
    if perfil_atual.usuario_id:
        conditions |= Q(
            usuario_id=perfil_atual.usuario_id,
            perfil_id=perfil_alvo.id,
            tipo="BLOQUEIO",
        )
    if perfil_alvo.usuario_id:
        conditions |= Q(
            usuario_id=perfil_alvo.usuario_id,
            perfil_id=perfil_atual.id,
            tipo="BLOQUEIO",
        )
    return bool(conditions) and AcaoPerfil.objects.filter(conditions).exists()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_foto_perfil(request, perfil_id):
    perfil = (
        PerfilNKATA.objects
        .select_related("pedido", "usuario")
        .filter(id=perfil_id)
        .first()
    )
    if not perfil:
        return Response({"detail": "Fotografia não encontrada."}, status=404)

    perfil_atual = getattr(request.user, "perfil_nkata", None)
    is_owner = perfil.usuario_id == request.user.id
    if not request.user.is_staff:
        if not is_owner and (perfil.status != "ATIVO" or not perfil.visivel):
            return Response({"detail": "Fotografia não encontrada."}, status=404)
        if not is_owner and _blocked(perfil_atual, perfil):
            return Response({"detail": "Fotografia não encontrada."}, status=404)

    if not perfil.foto_principal:
        return Response({"detail": "Fotografia não encontrada."}, status=404)
    return _stream(perfil.foto_principal) or Response(
        {"detail": "Fotografia não encontrada."},
        status=404,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_media_pedido_admin(request, pedido_id, field_name):
    if field_name not in ADMIN_MEDIA_FIELDS:
        return Response({"detail": "Documento não encontrado."}, status=404)
    pedido = PedidoEntrada.objects.filter(id=pedido_id).first()
    field_file = getattr(pedido, field_name, None) if pedido else None
    if not field_file:
        return Response({"detail": "Documento não encontrado."}, status=404)
    return _stream(field_file, private_cache=False) or Response(
        {"detail": "Documento não encontrado."},
        status=404,
    )


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_media_nkata_id_admin(request, verification_id, field_name):
    if field_name not in NKATA_ID_MEDIA_FIELDS:
        return Response({"detail": "Documento não encontrado."}, status=404)
    verification = VerificacaoIdentidadeNKATA.objects.filter(
        id=verification_id
    ).first()
    field_file = getattr(verification, field_name, None) if verification else None
    if not field_file:
        return Response({"detail": "Documento não encontrado."}, status=404)
    return _stream(field_file, private_cache=False) or Response(
        {"detail": "Documento não encontrado."},
        status=404,
    )
