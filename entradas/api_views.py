from PIL import Image, UnidentifiedImageError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from .models import (
    AcaoPerfil,
    DenunciaPerfil,
    MatchPerfil,
    MensagemMatch,
    PerfilNKATA,
)
from .media_validation import image_dimensions_are_safe, sanitized_image_upload
from .serializers import (
    MatchSerializer,
    MensagemMatchSerializer,
    MinhaContaSerializer,
    PerfilDetalheSerializer,
    PerfilResumoSerializer,
)
from .throttles import LoginRateThrottle


MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
MIN_PROFILE_PHOTO_SIDE = 500
ALLOWED_PROFILE_PHOTO_FORMATS = {"JPEG", "PNG", "WEBP"}
REPORT_REASONS = {value for value, _label in DenunciaPerfil.MOTIVOS}


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
            "is_staff": request.user.is_staff,
            "is_superuser": request.user.is_superuser,
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

    if not conditions:
        return False

    return AcaoPerfil.objects.filter(conditions).exists()


def _encerrar_matches_entre(perfil_a, perfil_b):
    return MatchPerfil.objects.filter(
        Q(perfil_1=perfil_a, perfil_2=perfil_b)
        | Q(perfil_1=perfil_b, perfil_2=perfil_a),
        status="ATIVO",
    ).update(status="ENCERRADO")


def _remover_interesses_entre(perfil_a, perfil_b):
    conditions = Q()

    if perfil_a.usuario_id:
        conditions |= Q(
            usuario_id=perfil_a.usuario_id,
            perfil_id=perfil_b.id,
            tipo="INTERESSE",
        )

    if perfil_b.usuario_id:
        conditions |= Q(
            usuario_id=perfil_b.usuario_id,
            perfil_id=perfil_a.id,
            tipo="INTERESSE",
        )

    if conditions:
        AcaoPerfil.objects.filter(conditions).delete()


def _criar_match_se_mutuo(perfil_alvo, usuario_atual):
    perfil_atual = _perfil_do_utilizador(usuario_atual)

    if (
        not perfil_atual
        or not perfil_alvo.usuario_id
        or perfil_atual.id == perfil_alvo.id
        or _bloqueio_entre_perfis(perfil_atual, perfil_alvo)
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


def _validar_foto_perfil(foto):
    if not foto:
        return "Escolha uma fotografia."

    if foto.size > MAX_PROFILE_PHOTO_SIZE:
        return "A fotografia deve ter no máximo 5 MB."

    try:
        image = Image.open(foto)
        image.verify()
        foto.seek(0)

        image = Image.open(foto)
        width, height = image.size
        image_format = (image.format or "").upper()
        safe_dimensions = image_dimensions_are_safe(image)
        foto.seek(0)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return "O ficheiro enviado não é uma fotografia válida."

    if image_format not in ALLOWED_PROFILE_PHOTO_FORMATS:
        return "Use uma fotografia em JPG, PNG ou WEBP."

    if not safe_dimensions:
        return "A fotografia possui dimensões demasiado grandes."

    if width < MIN_PROFILE_PHOTO_SIDE or height < MIN_PROFILE_PHOTO_SIDE:
        return "A fotografia deve ter pelo menos 500 × 500 píxeis."

    return None


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_status(request):
    try:
        connection.ensure_connection()
        database_ready = connection.is_usable()
    except Exception:  # A resposta não deve expor detalhes da infraestrutura.
        database_ready = False

    return Response(
        {
            "name": "NKATA API",
            "status": "online" if database_ready else "degraded",
            "database_ready": database_ready,
        },
        status=200 if database_ready else 503,
    )


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def api_session(request):
    return Response(_dados_da_sessao(request))


@csrf_protect
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([LoginRateThrottle])
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


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def api_minha_conta(request):
    perfil = _perfil_do_utilizador(request.user)

    if not perfil:
        return Response(
            {"detail": "A sua conta ainda não tem um perfil NKATA."},
            status=404,
        )

    if request.method == "PATCH":
        serializer = MinhaContaSerializer(
            perfil,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        perfil = serializer.save()

        if "nome_publico" in serializer.validated_data:
            request.user.first_name = perfil.nome_publico[:150]
            request.user.save(update_fields=["first_name"])

    serializer = MinhaContaSerializer(
        perfil,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_atualizar_foto_perfil(request):
    perfil = _perfil_do_utilizador(request.user)

    if not perfil:
        return Response(
            {"detail": "A sua conta ainda não tem um perfil NKATA."},
            status=404,
        )

    foto = request.FILES.get("foto")
    erro = _validar_foto_perfil(foto)
    if erro:
        return Response({"foto": [erro]}, status=400)
    try:
        foto = sanitized_image_upload(foto)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return Response({"foto": ["Não foi possível preparar esta fotografia."]}, status=400)

    public_preview_was_enabled = perfil.destaque_publico
    pedido = perfil.pedido
    foto_anterior = pedido.foto_perfil
    nome_anterior = foto_anterior.name if foto_anterior else ""
    storage = foto_anterior.storage if foto_anterior else pedido._meta.get_field("foto_perfil").storage

    pedido.foto_perfil = foto
    pedido.save(update_fields=["foto_perfil", "atualizado_em"])

    novo_nome = pedido.foto_perfil.name
    if nome_anterior and nome_anterior != novo_nome and storage.exists(nome_anterior):
        storage.delete(nome_anterior)

    perfil.destaque_publico = False
    perfil.foto_destaque_publico_aprovada = False
    perfil.save(update_fields=[
        "destaque_publico",
        "foto_destaque_publico_aprovada",
        "atualizado_em",
    ])

    serializer = MinhaContaSerializer(
        perfil,
        context={"request": request},
    )
    return Response({
        "message": (
            "Fotografia atualizada. A apresentação pública foi desligada até a nova foto ser aprovada."
            if public_preview_was_enabled
            else "Fotografia atualizada. A nova foto aguarda aprovação para apresentação pública."
        ),
        "account": serializer.data,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_perfis(request):
    perfis = PerfilNKATA.objects.filter(
        status="ATIVO",
        visivel=True,
    ).select_related("pedido", "usuario")

    if request.user.is_authenticated:
        perfil_atual = _perfil_do_utilizador(request.user)
        bloqueados = AcaoPerfil.objects.filter(
            usuario=request.user,
            tipo="BLOQUEIO",
        ).values_list("perfil_id", flat=True)

        perfis = perfis.exclude(id__in=bloqueados)

        if perfil_atual:
            bloqueadores = AcaoPerfil.objects.filter(
                perfil=perfil_atual,
                tipo="BLOQUEIO",
            ).exclude(usuario=None).values_list("usuario_id", flat=True)
            perfis = perfis.exclude(usuario_id__in=bloqueadores).exclude(id=perfil_atual.id)

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
        perfil = PerfilNKATA.objects.select_related("pedido", "usuario").get(
            id=perfil_id,
            status="ATIVO",
            visivel=True,
        )
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    perfil_atual = _perfil_do_utilizador(request.user)
    if (
        request.user.is_authenticated
        and perfil_atual
        and perfil_atual.id != perfil.id
        and _bloqueio_entre_perfis(perfil_atual, perfil)
    ):
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

    if _bloqueio_entre_perfis(perfil_atual, perfil_alvo):
        return Response(
            {"detail": "Esta interação não está disponível."},
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


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_denunciar_perfil(request, perfil_id):
    perfil_atual = _perfil_do_utilizador(request.user)

    try:
        perfil_alvo = PerfilNKATA.objects.get(id=perfil_id)
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    if perfil_atual and perfil_atual.id == perfil_alvo.id:
        return Response(
            {"detail": "Não pode denunciar o seu próprio perfil."},
            status=403,
        )

    motivo = str(request.data.get("motivo", "")).strip().upper()
    detalhes = " ".join(str(request.data.get("detalhes", "")).split())

    if motivo not in REPORT_REASONS:
        return Response({"motivo": ["Escolha um motivo válido."]}, status=400)

    if motivo == "OUTRO" and len(detalhes) < 10:
        return Response(
            {"detalhes": ["Explique brevemente o que aconteceu."]},
            status=400,
        )

    if len(detalhes) > 1000:
        return Response(
            {"detalhes": ["Os detalhes devem ter no máximo 1000 caracteres."]},
            status=400,
        )

    denuncia_aberta = DenunciaPerfil.objects.filter(
        denunciante=request.user,
        perfil=perfil_alvo,
        analisada=False,
    ).exists()

    if denuncia_aberta:
        return Response(
            {"detail": "A sua denúncia sobre este perfil já foi recebida."},
            status=409,
        )

    DenunciaPerfil.objects.create(
        denunciante=request.user,
        perfil=perfil_alvo,
        motivo=motivo,
        detalhes=detalhes,
    )

    return Response({
        "ok": True,
        "message": "Denúncia enviada. A equipa vai analisar a situação.",
    }, status=201)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_bloquear_perfil(request, perfil_id):
    perfil_atual = _perfil_do_utilizador(request.user)

    if not perfil_atual:
        return Response(
            {"detail": "A sua conta ainda não tem um perfil NKATA."},
            status=404,
        )

    try:
        perfil_alvo = PerfilNKATA.objects.select_related("usuario").get(id=perfil_id)
    except PerfilNKATA.DoesNotExist:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    if perfil_atual.id == perfil_alvo.id:
        return Response(
            {"detail": "Não pode bloquear o seu próprio perfil."},
            status=403,
        )

    if not request.session.session_key:
        request.session.create()

    bloqueio = AcaoPerfil.objects.filter(
        perfil=perfil_alvo,
        usuario=request.user,
        tipo="BLOQUEIO",
    ).first()

    if not bloqueio:
        AcaoPerfil.objects.create(
            perfil=perfil_alvo,
            usuario=request.user,
            tipo="BLOQUEIO",
            session_key=request.session.session_key,
        )

    _remover_interesses_entre(perfil_atual, perfil_alvo)
    _encerrar_matches_entre(perfil_atual, perfil_alvo)

    return Response({
        "ok": True,
        "message": "Perfil bloqueado. Esta pessoa deixou de aparecer para si.",
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

    bloqueados = AcaoPerfil.objects.filter(
        usuario=request.user,
        tipo="BLOQUEIO",
    ).values_list("perfil_id", flat=True)
    interesses = interesses.exclude(perfil_id__in=bloqueados)

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


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_encerrar_match(request, match_id):
    match = _match_do_utilizador(request, match_id)

    if not match:
        return Response({"detail": "Ligação não encontrada."}, status=404)

    perfil_atual = _perfil_do_utilizador(request.user)
    outro_perfil = (
        match.perfil_2
        if match.perfil_1_id == perfil_atual.id
        else match.perfil_1
    )

    match.status = "ENCERRADO"
    match.save(update_fields=["status", "atualizado_em"])
    _remover_interesses_entre(perfil_atual, outro_perfil)

    return Response({
        "ok": True,
        "message": "A ligação foi encerrada. A conversa deixou de estar disponível.",
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
