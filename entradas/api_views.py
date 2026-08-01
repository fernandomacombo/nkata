from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AcaoPerfil, MatchPerfil, MensagemMatch, PerfilNKATA
from .serializers import (
    MatchSerializer,
    MensagemMatchSerializer,
    PerfilDetalheSerializer,
    PerfilResumoSerializer,
)


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


def _dados_da_sessao(request):
    perfil = _perfil_do_utilizador(request.user)

    if not request.user.is_authenticated:
        return {
            "authenticated": False,
            "user": None,
            "profile": None,
        }

    return {
        "authenticated": True,
        "user": {
            "id": request.user.id,
            "name": request.user.first_name or request.user.get_username(),
            "email": request.user.email,
        },
        "profile": (
            {
                "id": perfil.id,
                "name": perfil.nome_publico,
                "city": perfil.cidade,
                "status": perfil.status,
                "visible": perfil.visivel,
            }
            if perfil
            else None
        ),
    }


def _criar_match_se_mutuo(perfil_alvo, usuario_atual):
    perfil_atual = _perfil_do_utilizador(usuario_atual)

    if (
        not perfil_atual
        or not perfil_alvo.usuario_id
        or perfil_atual.id == perfil_alvo.id
    ):
        return None

    interesse_mutuo = AcaoPerfil.objects.filter(
        perfil=perfil_atual,
        usuario=perfil_alvo.usuario,
        tipo="INTERESSE",
    ).exists()

    if not interesse_mutuo:
        return None

    perfil_1, perfil_2 = sorted(
        [perfil_atual, perfil_alvo],
        key=lambda perfil: perfil.id,
    )

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


def _match_do_utilizador(request, match_id):
    perfil = _perfil_do_utilizador(request.user)

    if not perfil:
        return None

    return (
        MatchPerfil.objects
        .filter(
            Q(perfil_1=perfil) | Q(perfil_2=perfil),
            id=match_id,
            status="ATIVO",
        )
        .select_related(
            "perfil_1",
            "perfil_1__pedido",
            "perfil_1__usuario",
            "perfil_2",
            "perfil_2__pedido",
            "perfil_2__usuario",
        )
        .first()
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_status(request):
    return Response({
        "name": "NKATA API",
        "status": "online",
        "frontend_target": "React + Tailwind",
        "backend": "Django REST API",
    })


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_session(request):
    return Response(_dados_da_sessao(request))


@csrf_protect
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def api_login(request):
    email = str(request.data.get("email", "")).strip()
    password = str(request.data.get("password", ""))

    if not email or not password:
        return Response(
            {"detail": "Preencha o email e a palavra-passe."},
            status=400,
        )

    user_record = User.objects.filter(email__iexact=email).first()

    if not user_record:
        return Response(
            {"detail": "Email ou palavra-passe incorretos."},
            status=400,
        )

    user = authenticate(
        request,
        username=user_record.username,
        password=password,
    )

    if user is None:
        return Response(
            {"detail": "Email ou palavra-passe incorretos."},
            status=400,
        )

    if not user.is_active:
        return Response(
            {"detail": "Esta conta não está ativa."},
            status=403,
        )

    login(request, user)
    return Response(_dados_da_sessao(request))


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_logout(request):
    logout(request)
    return Response({"ok": True})


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

    serializer = PerfilDetalheSerializer(perfil, context={"request": request})
    data = dict(serializer.data)

    if request.user.is_authenticated:
        data["interesse_ativo"] = AcaoPerfil.objects.filter(
            perfil=perfil,
            usuario=request.user,
            tipo="INTERESSE",
        ).exists()
    else:
        data["interesse_ativo"] = False

    return Response(data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
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

    if not request.session.session_key:
        request.session.create()

    interesse = AcaoPerfil.objects.filter(
        perfil=perfil_alvo,
        tipo="INTERESSE",
    ).filter(
        Q(usuario=request.user) | Q(session_key=request.session.session_key)
    ).first()

    if interesse:
        interesse.delete()
        return Response({
            "ok": True,
            "active": False,
            "match": False,
            "message": "Interesse removido.",
        })

    AcaoPerfil.objects.create(
        perfil=perfil_alvo,
        tipo="INTERESSE",
        usuario=request.user,
        session_key=request.session.session_key,
    )

    match = _criar_match_se_mutuo(
        perfil_alvo=perfil_alvo,
        usuario_atual=request.user,
    )

    return Response({
        "ok": True,
        "active": True,
        "match": bool(match),
        "match_id": match.id if match else None,
        "message": (
            "É um match. O interesse é mútuo."
            if match
            else "O seu interesse foi registado."
        ),
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_meus_interesses(request):
    interesses = AcaoPerfil.objects.filter(
        usuario=request.user,
        tipo="INTERESSE",
        perfil__status="ATIVO",
        perfil__visivel=True,
    ).select_related("perfil", "perfil__pedido", "perfil__usuario")

    perfis = [interesse.perfil for interesse in interesses]
    serializer = PerfilResumoSerializer(
        perfis,
        many=True,
        context={"request": request},
    )

    return Response({
        "count": len(perfis),
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_meus_matches(request):
    perfil = _perfil_do_utilizador(request.user)

    if not perfil:
        return Response({"detail": "A sua conta ainda não tem um perfil NKATA."}, status=404)

    matches = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        status="ATIVO",
    ).select_related(
        "perfil_1",
        "perfil_1__pedido",
        "perfil_1__usuario",
        "perfil_2",
        "perfil_2__pedido",
        "perfil_2__usuario",
    ).prefetch_related("mensagens").order_by("-atualizado_em")

    serializer = MatchSerializer(
        matches,
        many=True,
        context={"request": request},
    )

    return Response({
        "count": matches.count(),
        "results": serializer.data,
    })


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_conversa_match(request, match_id):
    match = _match_do_utilizador(request, match_id)

    if not match:
        return Response({"detail": "Conversa não encontrada."}, status=404)

    if request.method == "POST":
        texto = str(request.data.get("texto", "")).strip()

        if not texto:
            return Response({"detail": "Escreva uma mensagem."}, status=400)

        if len(texto) > 1200:
            return Response(
                {"detail": "A mensagem deve ter no máximo 1200 caracteres."},
                status=400,
            )

        mensagem = MensagemMatch.objects.create(
            match=match,
            remetente=request.user,
            texto=texto,
        )
        match.save(update_fields=["atualizado_em"])

        serializer = MensagemMatchSerializer(
            mensagem,
            context={"request": request},
        )
        return Response(serializer.data, status=201)

    match.mensagens.filter(lida=False).exclude(remetente=request.user).update(lida=True)

    mensagens = match.mensagens.select_related(
        "remetente",
        "remetente__perfil_nkata",
    ).all()

    return Response({
        "match": MatchSerializer(match, context={"request": request}).data,
        "results": MensagemMatchSerializer(
            mensagens,
            many=True,
            context={"request": request},
        ).data,
    })
