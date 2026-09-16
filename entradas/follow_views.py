from django.db import transaction
from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, PerfilNKATA
from .serializers import PerfilResumoSerializer
from .user_roles import active_member_profile_for_user


def _perfil_do_utilizador(user):
    return active_member_profile_for_user(user)


def _bloqueio_entre_perfis(perfil_a, perfil_b):
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


def _ids_bloqueados_para(user, perfil_atual):
    bloqueados = set(
        AcaoPerfil.objects.filter(
            usuario=user,
            tipo="BLOQUEIO",
        ).values_list("perfil_id", flat=True)
    )

    bloqueadores = set(
        AcaoPerfil.objects.filter(
            perfil=perfil_atual,
            tipo="BLOQUEIO",
            usuario__isnull=False,
        ).values_list("usuario_id", flat=True)
    )
    return bloqueados, bloqueadores


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_perfis_seguidos(request):
    perfil_atual = _perfil_do_utilizador(request.user)
    if not perfil_atual or perfil_atual.status != "ATIVO":
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )

    bloqueados, bloqueadores = _ids_bloqueados_para(request.user, perfil_atual)

    actions = (
        AcaoPerfil.objects
        .filter(
            usuario=request.user,
            tipo="SEGUIR",
            perfil__status="ATIVO",
            perfil__visivel=True,
        )
        .select_related("perfil", "perfil__pedido", "perfil__usuario")
        .order_by("-criado_em")
    )

    if bloqueados:
        actions = actions.exclude(perfil_id__in=bloqueados)
    if bloqueadores:
        actions = actions.exclude(perfil__usuario_id__in=bloqueadores)

    perfis = []
    seen = set()
    for action in actions:
        if action.perfil_id == perfil_atual.id or action.perfil_id in seen:
            continue
        seen.add(action.perfil_id)
        perfis.append(action.perfil)

    serializer = PerfilResumoSerializer(
        perfis,
        many=True,
        context={"request": request},
    )
    return Response({
        "count": len(perfis),
        "results": serializer.data,
    })


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def api_alternar_seguir(request, perfil_id):
    try:
        perfil_alvo = PerfilNKATA.objects.select_related("usuario").get(
            id=perfil_id,
            status="ATIVO",
            visivel=True,
        )
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    perfil_atual = _perfil_do_utilizador(request.user)
    if not perfil_atual or perfil_atual.status != "ATIVO":
        return Response(
            {"detail": "A sua conta ainda não tem um perfil ativo no NKATA."},
            status=403,
        )

    if perfil_atual.id == perfil_alvo.id:
        return Response(
            {"detail": "Não pode seguir o seu próprio perfil."},
            status=403,
        )

    if _bloqueio_entre_perfis(perfil_atual, perfil_alvo):
        return Response(
            {"detail": "Esta interação não está disponível."},
            status=403,
        )

    existing = AcaoPerfil.objects.filter(
        perfil=perfil_alvo,
        usuario=request.user,
        tipo="SEGUIR",
    )

    if request.method == "GET":
        return Response({
            "active": existing.exists(),
            "profile_id": perfil_alvo.id,
        })

    if existing.exists():
        existing.delete()
        return Response({
            "ok": True,
            "active": False,
            "message": f"Deixou de seguir {perfil_alvo.nome_publico}.",
        })

    if not request.session.session_key:
        request.session.create()

    AcaoPerfil.objects.create(
        perfil=perfil_alvo,
        usuario=request.user,
        tipo="SEGUIR",
        session_key=request.session.session_key,
    )

    return Response({
        "ok": True,
        "active": True,
        "message": f"Agora está a seguir {perfil_alvo.nome_publico}.",
    })
