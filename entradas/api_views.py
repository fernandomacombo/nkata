from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import MatchPerfil, PerfilNKATA
from .serializers import MatchSerializer, PerfilResumoSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_status(request):
    return Response({
        "name": "NKATA API",
        "status": "online",
        "frontend_target": "React + Tailwind",
        "backend": "Django REST API",
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_perfis(request):
    perfis = PerfilNKATA.objects.filter(
        status="ATIVO",
        visivel=True,
    ).select_related("pedido", "usuario")

    serializer = PerfilResumoSerializer(
        perfis,
        many=True,
        context={"request": request},
    )

    return Response({
        "count": perfis.count(),
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_perfil_detalhe(request, perfil_id):
    try:
        perfil = PerfilNKATA.objects.select_related("pedido", "usuario").get(
            id=perfil_id,
            status="ATIVO",
            visivel=True,
        )
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    serializer = PerfilResumoSerializer(perfil, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_meus_matches(request):
    perfil = getattr(request.user, "perfil_nkata", None)

    if not perfil:
        return Response({"detail": "Conta sem perfil NKATA associado."}, status=404)

    matches = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        status="ATIVO",
    ).select_related(
        "perfil_1",
        "perfil_1__pedido",
        "perfil_2",
        "perfil_2__pedido",
    ).prefetch_related("mensagens")

    serializer = MatchSerializer(
        matches,
        many=True,
        context={"request": request},
    )

    return Response({
        "count": matches.count(),
        "results": serializer.data,
    })
