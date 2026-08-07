from django.db import transaction
from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, PerfilNKATA


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


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


@api_view(["POST"])
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

    if existing.exists():
        # Remove todas as ocorrências antigas da mesma conta, caso existam
        # registos legados associados a sessões diferentes.
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
