from PIL import Image, UnidentifiedImageError
from django.views.decorators.csrf import csrf_protect
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
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


@csrf_protect
@api_view(["POST"])
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
                    "Use o mesmo email para acompanhar o pedido ou fale com a equipa NKATA."
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
        "message": (
            "Recebemos o seu pedido. A equipa NKATA vai analisar os dados "
            "e entrar em contacto pelo email informado."
        ),
    }, status=201)
