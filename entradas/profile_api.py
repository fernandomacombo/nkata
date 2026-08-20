from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, PerfilNKATA
from .profile_gallery_api import gallery_for_profile_viewer
from .serializers import PerfilDetalheSerializer, PerfilResumoSerializer


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


def _filtro_perfil_proprio(user):
    """Identifica o próprio perfil mesmo em contas antigas parcialmente ligadas.

    A ligação normal é PerfilNKATA.usuario == user. Como proteção adicional,
    PedidoEntrada.email é único e permite reconhecer dados antigos que ainda
    não tenham a relação usuario preenchida corretamente.
    """
    filtro = Q(usuario_id=user.id)
    email = str(getattr(user, "email", "") or "").strip()
    if email:
        filtro |= Q(pedido__email__iexact=email)
    return filtro


def _eh_perfil_proprio(user, perfil):
    if not user or not user.is_authenticated or not perfil:
        return False

    if perfil.usuario_id == user.id:
        return True

    email = str(getattr(user, "email", "") or "").strip().lower()
    pedido_email = str(getattr(perfil.pedido, "email", "") or "").strip().lower()
    return bool(email and pedido_email and email == pedido_email)


def _bloqueio_entre_perfis(perfil_a, perfil_b):
    if not perfil_a or not perfil_b:
        return False

    conditions = Q()
    if perfil_a.usuario_id:
        conditions |= Q(
            usuario_id=perfil_a.usuario_id,
            perfil_id=perfil_b.id,
            tipo="BLOQUEIO",
        )
    if perfil_b.usuario_id:
        conditions |= Q(
            usuario_id=perfil_b.usuario_id,
            perfil_id=perfil_a.id,
            tipo="BLOQUEIO",
        )

    return bool(conditions) and AcaoPerfil.objects.filter(conditions).exists()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_perfis(request):
    perfis = PerfilNKATA.objects.filter(
        status="ATIVO",
        visivel=True,
    ).select_related("pedido", "usuario", "usuario__preferencias_nkata")

    if request.user.is_authenticated:
        # Regra principal: a pessoa nunca se descobre a si própria.
        perfis = perfis.exclude(_filtro_perfil_proprio(request.user))

        bloqueados = AcaoPerfil.objects.filter(
            usuario=request.user,
            tipo="BLOQUEIO",
        ).values_list("perfil_id", flat=True)
        perfis = perfis.exclude(id__in=bloqueados)

        perfil_atual = _perfil_do_utilizador(request.user)
        if perfil_atual:
            bloqueadores = AcaoPerfil.objects.filter(
                perfil=perfil_atual,
                tipo="BLOQUEIO",
            ).exclude(usuario=None).values_list("usuario_id", flat=True)
            perfis = perfis.exclude(usuario_id__in=bloqueadores)

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
@permission_classes([permissions.IsAuthenticated])
def api_perfil_detalhe(request, perfil_id):
    try:
        perfil = PerfilNKATA.objects.select_related(
            "pedido",
            "usuario",
            "usuario__preferencias_nkata",
        ).get(
            id=perfil_id,
            status="ATIVO",
            visivel=True,
        )
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    if request.user.is_authenticated and _eh_perfil_proprio(request.user, perfil):
        # O próprio perfil pertence à área Minha conta, não à descoberta.
        return Response({"detail": "Perfil não encontrado."}, status=404)

    perfil_atual = _perfil_do_utilizador(request.user)
    if (
        request.user.is_authenticated
        and perfil_atual
        and _bloqueio_entre_perfis(perfil_atual, perfil)
    ):
        return Response({"detail": "Perfil não encontrado."}, status=404)

    serializer = PerfilDetalheSerializer(perfil, context={"request": request})
    data = dict(serializer.data)
    data.update(gallery_for_profile_viewer(request, perfil))

    if request.user.is_authenticated:
        data["interesse_ativo"] = AcaoPerfil.objects.filter(
            perfil=perfil,
            usuario=request.user,
            tipo="INTERESSE",
        ).exists()
        data["seguindo"] = AcaoPerfil.objects.filter(
            perfil=perfil,
            usuario=request.user,
            tipo="SEGUIR",
        ).exists()
    else:
        data["interesse_ativo"] = False
        data["seguindo"] = False

    return Response(data)
