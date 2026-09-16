from django.db import transaction
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, PerfilNKATA
from .serializers import PerfilResumoSerializer


SAVED_ACTION = "GUARDADO"


def _stable_user_key(user):
    return f"user:{user.id}"


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_perfis_guardados(request):
    actions = (
        AcaoPerfil.objects
        .filter(
            usuario=request.user,
            tipo=SAVED_ACTION,
            perfil__status="ATIVO",
            perfil__visivel=True,
        )
        .select_related("perfil", "perfil__pedido", "perfil__usuario")
        .order_by("-criado_em")
    )

    profiles = [action.perfil for action in actions]
    serializer = PerfilResumoSerializer(
        profiles,
        many=True,
        context={"request": request},
    )

    return Response({
        "count": len(profiles),
        "results": serializer.data,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def api_alternar_perfil_guardado(request, perfil_id):
    try:
        profile = PerfilNKATA.objects.select_related("usuario").get(
            id=perfil_id,
            status="ATIVO",
            visivel=True,
        )
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    current_profile = getattr(request.user, "perfil_nkata", None)
    if current_profile and current_profile.id == profile.id:
        return Response(
            {"detail": "Não é necessário guardar o seu próprio perfil."},
            status=403,
        )

    saved = AcaoPerfil.objects.filter(
        perfil=profile,
        usuario=request.user,
        tipo=SAVED_ACTION,
    ).first()

    if saved:
        saved.delete()
        return Response({
            "ok": True,
            "active": False,
            "profile_id": profile.id,
            "message": "Perfil removido dos guardados.",
        })

    AcaoPerfil.objects.create(
        perfil=profile,
        usuario=request.user,
        tipo=SAVED_ACTION,
        session_key=_stable_user_key(request.user),
    )

    return Response({
        "ok": True,
        "active": True,
        "profile_id": profile.id,
        "message": "Perfil guardado na sua conta.",
    })
