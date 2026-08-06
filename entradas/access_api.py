import uuid

from PIL import Image, UnidentifiedImageError
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .forms import PedidoEntradaForm
from .models import PedidoEntrada


MAX_ACCESS_IMAGE_SIZE = 6 * 1024 * 1024
ALLOWED_ACCESS_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
IMAGE_FIELDS = [
    "foto_perfil",
    "foto_extra_1",
    "foto_extra_2",
    "foto_extra_3",
    "bi_frente",
    "bi_verso",
    "selfie_com_bi",
]

STATUS_CONTENT = {
    "PENDENTE": {
        "title": "O seu pedido foi recebido.",
        "message": (
            "Os dados chegaram em segurança. A equipa ainda vai iniciar a análise."
        ),
        "tone": "waiting",
        "stage": 1,
    },
    "EM_ANALISE": {
        "title": "A análise está em andamento.",
        "message": (
            "A equipa está a confirmar os dados, fotografias e documentos enviados."
        ),
        "tone": "review",
        "stage": 2,
    },
    "PRECISA_CORRIGIR": {
        "title": "Precisamos de uma correção.",
        "message": (
            "Há informação que precisa ser atualizada. A equipa entrará em contacto "
            "pelo email usado no pedido com as orientações necessárias."
        ),
        "tone": "attention",
        "stage": 3,
    },
    "APROVADO": {
        "title": "O seu pedido foi aprovado.",
        "message": (
            "A entrada foi aprovada. Consulte o seu email para os dados de acesso "
            "ou entre com a conta que recebeu da equipa."
        ),
        "tone": "success",
        "stage": 4,
    },
    "RECUSADO": {
        "title": "O pedido não foi aprovado.",
        "message": (
            "A análise foi concluída e o pedido não pôde ser aprovado neste momento."
        ),
        "tone": "closed",
        "stage": 3,
    },
    "BLOQUEADO": {
        "title": "O pedido está indisponível.",
        "message": (
            "Este pedido não pode continuar. Para esclarecer a situação, contacte "
            "a equipa NKATA pelo canal oficial."
        ),
        "tone": "closed",
        "stage": 3,
    },
}


def _normalizar_erros(form):
    errors = {}

    for field, messages in form.errors.get_json_data().items():
        readable = []
        for item in messages:
            message = item.get("message", "Revise este campo.")
            if field == "email" and "already exists" in message.lower():
                message = "Já existe um pedido associado a este email."
            readable.append(message)
        errors[field] = readable

    return errors


def _validar_imagem(upload):
    if not upload:
        return "Escolha uma imagem."

    if upload.size > MAX_ACCESS_IMAGE_SIZE:
        return "A imagem deve ter no máximo 6 MB."

    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
        image_format = (image.format or "").upper()
        upload.seek(0)
    except (UnidentifiedImageError, OSError, ValueError):
        return "O ficheiro escolhido não é uma imagem válida."

    if image_format not in ALLOWED_ACCESS_IMAGE_FORMATS:
        return "Use uma imagem em JPG, PNG ou WEBP."

    return None


def _status_payload(pedido):
    content = STATUS_CONTENT.get(
        pedido.status,
        {
            "title": "O pedido está a ser acompanhado.",
            "message": "Consulte novamente mais tarde para ver novas atualizações.",
            "tone": "waiting",
            "stage": 1,
        },
    )

    return {
        "codigo": str(pedido.token),
        "status": pedido.status,
        "status_label": pedido.get_status_display(),
        "title": content["title"],
        "message": content["message"],
        "tone": content["tone"],
        "stage": content["stage"],
        "created_at": pedido.criado_em,
        "updated_at": pedido.atualizado_em,
        "can_login": pedido.status == "APROVADO",
    }


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def api_pedir_acesso(request):
    image_errors = {}

    for field in IMAGE_FIELDS:
        error = _validar_imagem(request.FILES.get(field))
        if error:
            image_errors[field] = [error]

    if image_errors:
        return Response({
            "detail": "Revise as imagens antes de continuar.",
            "errors": image_errors,
        }, status=400)

    email = str(request.data.get("email", "")).strip().lower()
    if email and PedidoEntrada.objects.filter(email__iexact=email).exists():
        return Response({
            "detail": "Já recebemos um pedido com este email.",
            "errors": {
                "email": [
                    "Use o mesmo email e o código privado para acompanhar o pedido."
                ]
            },
        }, status=409)

    data = request.data.copy()
    if email:
        data["email"] = email

    form = PedidoEntradaForm(data, request.FILES)
    if not form.is_valid():
        return Response({
            "detail": "Há alguns campos que precisam da sua atenção.",
            "errors": _normalizar_erros(form),
        }, status=400)

    pedido = form.save()

    return Response({
        "ok": True,
        "pedido_id": pedido.id,
        "codigo": str(pedido.token),
        "email": pedido.email,
        "message": (
            "Recebemos o seu pedido. Guarde o código privado para acompanhar "
            "a análise sem precisar contactar a equipa."
        ),
    }, status=201)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def api_acompanhar_pedido(request):
    email = str(request.data.get("email", "")).strip().lower()
    raw_code = str(request.data.get("codigo", "")).strip()

    if not email or not raw_code:
        return Response(
            {"detail": "Informe o email e o código privado do pedido."},
            status=400,
        )

    try:
        code = uuid.UUID(raw_code)
    except (ValueError, AttributeError, TypeError):
        return Response(
            {"detail": "O email ou o código do pedido não está correto."},
            status=404,
        )

    pedido = PedidoEntrada.objects.filter(
        email__iexact=email,
        token=code,
    ).first()

    if not pedido:
        return Response(
            {"detail": "O email ou o código do pedido não está correto."},
            status=404,
        )

    return Response(_status_payload(pedido))
