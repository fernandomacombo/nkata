from django.db import transaction
from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, MatchPerfil, PerfilNKATA


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


def _match_entre(perfil_a, perfil_b):
    perfil_1, perfil_2 = sorted([perfil_a, perfil_b], key=lambda perfil: perfil.id)
    return MatchPerfil.objects.filter(
        perfil_1=perfil_1,
        perfil_2=perfil_2,
        status="ATIVO",
    ).first()


def _criar_match_se_mutuo(perfil_atual, perfil_alvo):
    if not perfil_alvo.usuario_id:
        return None

    interesse_mutuo = AcaoPerfil.objects.filter(
        perfil=perfil_atual,
        usuario=perfil_alvo.usuario,
        tipo="INTERESSE",
    ).exists()

    if not interesse_mutuo:
        return None

    perfil_1, perfil_2 = sorted([perfil_atual, perfil_alvo], key=lambda perfil: perfil.id)
    match, criado = MatchPerfil.objects.get_or_create(
        perfil_1=perfil_1,
        perfil_2=perfil_2,
        defaults={
            "tipo_origem": "INTERESSE",
            "status": "ATIVO",
        },
    )

    if not criado and match.status != "ATIVO":
        match.status = "ATIVO"
        match.tipo_origem = "INTERESSE"
        match.save(update_fields=["status", "tipo_origem", "atualizado_em"])

    return match


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@transaction.atomic
def api_alternar_interesse(request, perfil_id):
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
            {"detail": "Não pode demonstrar interesse no seu próprio perfil."},
            status=403,
        )

    if _bloqueio_entre_perfis(perfil_atual, perfil_alvo):
        return Response(
            {"detail": "Esta interação não está disponível."},
            status=403,
        )

    # Depois de um match, a ligação é administrada na conversa. Um toque
    # acidental no botão de interesse não deve desfazer a relação.
    match_existente = _match_entre(perfil_atual, perfil_alvo)
    if match_existente:
        return Response({
            "ok": True,
            "active": True,
            "match": True,
            "match_id": match_existente.id,
            "message": "Já existe um match entre vocês. Pode continuar pela conversa.",
        })

    if not request.session.session_key:
        request.session.create()

    # Numa conta autenticada, o utilizador é a fonte de verdade. A sessão
    # fica apenas como compatibilidade com dados antigos.
    interesse = AcaoPerfil.objects.filter(
        perfil=perfil_alvo,
        usuario=request.user,
        tipo="INTERESSE",
    ).first()

    if interesse:
        interesse.delete()
        return Response({
            "ok": True,
            "active": False,
            "match": False,
            "match_id": None,
            "message": "O interesse foi retirado.",
        })

    AcaoPerfil.objects.create(
        perfil=perfil_alvo,
        tipo="INTERESSE",
        usuario=request.user,
        session_key=request.session.session_key,
    )

    match = _criar_match_se_mutuo(perfil_atual, perfil_alvo)

    return Response({
        "ok": True,
        "active": True,
        "match": bool(match),
        "match_id": match.id if match else None,
        "message": (
            "É um match. O interesse é dos dois lados."
            if match
            else "Interesse enviado. A outra pessoa será avisada."
        ),
    })
