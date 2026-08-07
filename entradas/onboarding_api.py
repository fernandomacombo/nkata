from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .forms import QuestionarioEntradaForm
from .models import PedidoEntrada, PerfilNKATA


User = get_user_model()


def _pedido_aprovado(token):
    return PedidoEntrada.objects.filter(token=token, status="APROVADO").first()


def _nome_publico(nome_completo):
    partes = [parte for parte in str(nome_completo or "").strip().split() if parte]
    if not partes:
        return "Membro NKATA"
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[-1]}"


def _get_or_create_user(pedido):
    user = User.objects.filter(email__iexact=pedido.email).first()
    if user:
        return user

    base_username = pedido.email.split("@")[0][:80] or f"nkata_{pedido.id}"
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{suffix}"
        suffix += 1

    user = User.objects.create_user(
        username=username,
        email=pedido.email.lower(),
        password=None,
        first_name=pedido.nome_completo[:150],
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def _preparar_perfil(pedido, questionario):
    usuario = _get_or_create_user(pedido)
    perfil, _ = PerfilNKATA.objects.get_or_create(
        pedido=pedido,
        defaults={
            "usuario": usuario,
            "nome_publico": _nome_publico(pedido.nome_completo),
            "cidade": pedido.cidade,
            "idade": pedido.idade,
            "genero": pedido.genero,
            "objetivo": pedido.objetivo,
            "sobre_si": questionario.sobre_si,
            "o_que_valoriza": questionario.o_que_valoriza,
            "o_que_nao_aceita": questionario.o_que_nao_aceita,
            "status": "PAUSADO",
            "visivel": False,
        },
    )

    perfil.usuario = usuario
    perfil.nome_publico = perfil.nome_publico or _nome_publico(pedido.nome_completo)
    perfil.cidade = pedido.cidade
    perfil.idade = pedido.idade
    perfil.genero = pedido.genero
    perfil.objetivo = pedido.objetivo
    perfil.sobre_si = questionario.sobre_si
    perfil.o_que_valoriza = questionario.o_que_valoriza
    perfil.o_que_nao_aceita = questionario.o_que_nao_aceita
    perfil.save()
    return perfil


def _questionario_payload(pedido):
    questionario = getattr(pedido, "questionario", None)
    values = {}
    if questionario:
        values = {
            "disponibilidade": questionario.disponibilidade,
            "tem_filhos": questionario.tem_filhos,
            "aceita_pessoa_com_filhos": questionario.aceita_pessoa_com_filhos,
            "cidade_preferida": questionario.cidade_preferida,
            "faixa_etaria_preferida": questionario.faixa_etaria_preferida,
            "sobre_si": questionario.sobre_si,
            "o_que_valoriza": questionario.o_que_valoriza,
            "o_que_nao_aceita": questionario.o_que_nao_aceita,
            "aceita_regras": questionario.aceita_regras,
        }

    perfil = getattr(pedido, "perfil", None)
    senha_criada = bool(perfil and perfil.usuario and perfil.usuario.has_usable_password())

    return {
        "nome": _nome_publico(pedido.nome_completo),
        "status": pedido.status,
        "questionario_concluido": bool(questionario),
        "senha_criada": senha_criada,
        "values": values,
    }


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def api_questionario_aprovado(request, token):
    pedido = _pedido_aprovado(token)
    if not pedido:
        return Response(
            {"detail": "Este link não está disponível ou o pedido ainda não foi aprovado."},
            status=404,
        )

    if request.method == "GET":
        return Response(_questionario_payload(pedido))

    questionario_existente = getattr(pedido, "questionario", None)
    form = QuestionarioEntradaForm(request.data, instance=questionario_existente)
    if not form.is_valid():
        errors = {
            field: [item["message"] for item in items]
            for field, items in form.errors.get_json_data().items()
        }
        return Response(
            {
                "detail": "Há respostas que precisam da sua atenção.",
                "errors": errors,
            },
            status=400,
        )

    questionario = form.save(commit=False)
    questionario.pedido = pedido
    questionario.save()
    _preparar_perfil(pedido, questionario)

    return Response({
        "ok": True,
        "message": "As suas respostas foram guardadas com segurança.",
        "next": f"/criar-palavra-passe/{pedido.token}/",
    })


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def api_criar_palavra_passe(request, token):
    pedido = _pedido_aprovado(token)
    if not pedido:
        return Response(
            {"detail": "Este link não está disponível ou o pedido já não está aprovado."},
            status=404,
        )

    questionario = getattr(pedido, "questionario", None)
    if not questionario:
        return Response(
            {
                "detail": "Conclua primeiro o questionário de entrada.",
                "questionario_url": f"/questionario/{pedido.token}/",
            },
            status=409,
        )

    perfil = _preparar_perfil(pedido, questionario)
    usuario = perfil.usuario

    if request.method == "GET":
        return Response({
            "nome": perfil.nome_publico,
            "email": pedido.email,
            "senha_criada": usuario.has_usable_password(),
        })

    if usuario.has_usable_password():
        return Response(
            {"detail": "A palavra-passe desta conta já foi criada. Entre na sua conta."},
            status=409,
        )

    senha = str(request.data.get("password", ""))
    confirmar = str(request.data.get("confirm_password", ""))

    if senha != confirmar:
        return Response(
            {
                "detail": "As palavras-passe não coincidem.",
                "errors": {"confirm_password": ["Repita exatamente a mesma palavra-passe."]},
            },
            status=400,
        )

    try:
        validate_password(senha, user=usuario)
    except ValidationError as error:
        return Response(
            {
                "detail": "Escolha uma palavra-passe mais segura.",
                "errors": {"password": list(error.messages)},
            },
            status=400,
        )

    usuario.set_password(senha)
    usuario.save(update_fields=["password"])

    return Response({
        "ok": True,
        "message": "A sua conta está pronta. Já pode entrar no NKATA.",
        "login_url": "/entrar/",
    })
