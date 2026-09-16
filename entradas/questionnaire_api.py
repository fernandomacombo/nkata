from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from rest_framework import permissions
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response

from .throttles import TokenFlowRateThrottle

from .forms import QuestionarioEntradaForm
from .models import PedidoEntrada, PerfilNKATA, QuestionarioEntrada


User = get_user_model()


def _choice_payload(choices):
    return [{"value": value, "label": label} for value, label in choices]


def _form_errors(form):
    errors = {}
    for field, messages in form.errors.get_json_data().items():
        errors[field] = [item.get("message", "Revise este campo.") for item in messages]
    return errors


def _questionario_existente(pedido):
    try:
        return pedido.questionario
    except ObjectDoesNotExist:
        return None


def _perfil_existente(pedido):
    try:
        return pedido.perfil
    except ObjectDoesNotExist:
        return None


def _get_or_create_user(pedido):
    user = User.objects.filter(email__iexact=pedido.email).first()

    if user:
        perfil_existente = PerfilNKATA.objects.filter(usuario=user).exclude(pedido=pedido).first()
        if perfil_existente:
            raise ValidationError(
                "Este email já está associado a outra conta NKATA. Contacte a equipa para corrigir o acesso."
            )
        return user

    base_username = pedido.email.split("@")[0][:80] or f"nkata_{pedido.id}"
    username = base_username
    count = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{count}"
        count += 1

    user = User.objects.create_user(
        username=username,
        email=pedido.email,
        password=None,
        first_name=pedido.nome_completo[:150],
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def _questionnaire_payload(pedido):
    questionario = _questionario_existente(pedido)
    perfil = _perfil_existente(pedido)
    password_step_ready = bool(questionario and perfil and perfil.usuario_id)
    account_ready = bool(
        password_step_ready
        and perfil.usuario.has_usable_password()
        and perfil.status == "ATIVO"
        and perfil.visivel
    )

    values = {
        "disponibilidade": "",
        "tem_filhos": "",
        "aceita_pessoa_com_filhos": "",
        "cidade_preferida": "",
        "faixa_etaria_preferida": "",
        "sobre_si": "",
        "o_que_valoriza": "",
        "o_que_nao_aceita": "",
        "aceita_regras": False,
    }

    if questionario:
        for field in values:
            values[field] = getattr(questionario, field)

    return {
        "pedido": {
            "nome": pedido.nome_completo,
            "email": pedido.email,
            "cidade": pedido.cidade,
            "objetivo": pedido.get_objetivo_display(),
            "status": pedido.status,
            "status_label": pedido.get_status_display(),
        },
        "values": values,
        "choices": {
            "disponibilidade": _choice_payload(QuestionarioEntrada.DISPONIBILIDADE_CHOICES),
            "tem_filhos": _choice_payload(QuestionarioEntrada.FILHOS_CHOICES),
            "aceita_pessoa_com_filhos": _choice_payload(QuestionarioEntrada.ACEITA_FILHOS_CHOICES),
        },
        "questionnaire_complete": bool(questionario),
        "password_step_ready": password_step_ready,
        "account_ready": account_ready,
    }


def _pedido_aprovado(token):
    pedido = (
        PedidoEntrada.objects
        .select_related("questionario", "perfil__usuario")
        .filter(token=token)
        .first()
    )
    if not pedido:
        return None, Response(
            {"detail": "Este questionário não está disponível."},
            status=404,
        )
    if pedido.status != "APROVADO":
        return None, Response(
            {
                "detail": "Este questionário só fica disponível depois da aprovação do pedido.",
                "status": pedido.status,
                "status_label": pedido.get_status_display(),
            },
            status=403,
        )
    return pedido, None


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([TokenFlowRateThrottle])
def api_questionario(request, token):
    pedido, error_response = _pedido_aprovado(token)
    if error_response:
        return error_response

    if request.method == "GET":
        return Response(_questionnaire_payload(pedido))

    questionario = _questionario_existente(pedido)
    form = QuestionarioEntradaForm(request.data, instance=questionario)
    if not form.is_valid():
        return Response(
            {
                "detail": "Há respostas que precisam da sua atenção.",
                "errors": _form_errors(form),
            },
            status=400,
        )

    try:
        with transaction.atomic():
            questionario = form.save(commit=False)
            questionario.pedido = pedido
            questionario.save()

            user = _get_or_create_user(pedido)
            perfil, _ = PerfilNKATA.objects.get_or_create(
                pedido=pedido,
                defaults={
                    "usuario": user,
                    "nome_publico": pedido.nome_completo,
                    "cidade": pedido.cidade,
                    "idade": pedido.idade,
                    "genero": pedido.genero,
                    "objetivo": pedido.objetivo,
                    "sobre_si": questionario.sobre_si,
                    "o_que_valoriza": questionario.o_que_valoriza,
                    "o_que_nao_aceita": questionario.o_que_nao_aceita,
                    "status": "PAUSADO",
                    "visivel": False,
                    "foto_destaque_publico_aprovada": True,
                },
            )

            perfil.usuario = user
            perfil.nome_publico = pedido.nome_completo
            perfil.cidade = pedido.cidade
            perfil.idade = pedido.idade
            perfil.genero = pedido.genero
            perfil.objetivo = pedido.objetivo
            perfil.sobre_si = questionario.sobre_si
            perfil.o_que_valoriza = questionario.o_que_valoriza
            perfil.o_que_nao_aceita = questionario.o_que_nao_aceita
            if perfil.status != "BLOQUEADO":
                perfil.status = "PAUSADO"
            perfil.visivel = False
            perfil.save()
    except ValidationError as exc:
        return Response(
            {"detail": exc.messages[0] if exc.messages else "Não foi possível preparar a conta."},
            status=409,
        )

    return Response(
        {
            "ok": True,
            "message": "As suas respostas foram guardadas. Agora escolha a sua palavra-passe.",
            "next_step": "password",
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([TokenFlowRateThrottle])
def api_criar_senha_questionario(request, token):
    pedido, error_response = _pedido_aprovado(token)
    if error_response:
        return error_response

    questionario = _questionario_existente(pedido)
    perfil = _perfil_existente(pedido)
    if not questionario or not perfil or not perfil.usuario_id:
        return Response(
            {"detail": "Conclua primeiro o questionário para preparar a sua conta."},
            status=409,
        )

    user = perfil.usuario
    if user.has_usable_password():
        if perfil.status != "BLOQUEADO":
            PerfilNKATA.objects.filter(pk=perfil.pk).update(status="ATIVO", visivel=True)
        return Response(
            {
                "ok": True,
                "already_ready": True,
                "message": "A sua palavra-passe já foi criada. Pode entrar na sua conta.",
            }
        )

    password = str(request.data.get("password", ""))
    confirmation = str(request.data.get("confirmation", ""))

    if password != confirmation:
        return Response(
            {
                "detail": "As palavras-passe não coincidem.",
                "errors": {"confirmation": ["Escreva novamente a mesma palavra-passe."]},
            },
            status=400,
        )

    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return Response(
            {
                "detail": "Escolha uma palavra-passe mais segura.",
                "errors": {"password": list(exc.messages)},
            },
            status=400,
        )

    user.set_password(password)
    user.save(update_fields=["password"])
    perfil.refresh_from_db()

    return Response(
        {
            "ok": True,
            "message": "A sua conta está pronta. Já pode entrar no NKATA.",
            "profile_active": perfil.status == "ATIVO" and perfil.visivel,
        }
    )
