import uuid

from PIL import Image, UnidentifiedImageError
from rest_framework import permissions
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response

from .forms import PedidoEntradaForm
from .media_validation import image_dimensions_are_safe, sanitized_image_upload
from .models import PedidoEntrada, PerfilNKATA
from .throttles import AccessRequestRateThrottle, AccessStatusRateThrottle


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
        "message": "Os dados chegaram em segurança. A equipa ainda vai iniciar a análise.",
        "tone": "waiting",
        "stage": 1,
    },
    "EM_ANALISE": {
        "title": "A análise está em andamento.",
        "message": "A equipa está a confirmar os dados, fotografias e documentos enviados.",
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
            "A entrada foi aprovada. Falta concluir o questionário e criar a sua "
            "palavra-passe através do link privado fornecido pela equipa NKATA."
        ),
        "tone": "success",
        "stage": 4,
    },
    "RECUSADO": {
        "title": "O pedido não foi aprovado.",
        "message": "A análise foi concluída e o pedido não pôde ser aprovado neste momento.",
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
        safe_dimensions = image_dimensions_are_safe(image)
        upload.seek(0)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
        return "O ficheiro escolhido não é uma imagem válida."
    if image_format not in ALLOWED_ACCESS_IMAGE_FORMATS:
        return "Use uma imagem em JPG, PNG ou WEBP."
    if not safe_dimensions:
        return "A imagem possui dimensões demasiado grandes."
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

    perfil = (
        PerfilNKATA.objects
        .select_related("usuario")
        .filter(pedido=pedido)
        .first()
    )
    can_login = bool(
        pedido.status == "APROVADO"
        and perfil
        and perfil.usuario_id
        and perfil.usuario.has_usable_password()
    )

    message = content["message"]
    if pedido.status == "APROVADO" and can_login:
        message = "A sua conta está pronta. Já pode entrar no NKATA com o email e a palavra-passe que criou."

    return {
        "codigo": str(pedido.token),
        "status": pedido.status,
        "status_label": pedido.get_status_display(),
        "title": content["title"],
        "message": message,
        "tone": content["tone"],
        "stage": content["stage"],
        "created_at": pedido.criado_em,
        "updated_at": pedido.atualizado_em,
        "can_login": can_login,
        "next_action": "LOGIN" if can_login else "QUESTIONNAIRE" if pedido.status == "APROVADO" else None,
    }


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([AccessRequestRateThrottle])
def api_pedir_acesso(request):
    image_errors = {}
    safe_files = request.FILES.copy()
    for field in IMAGE_FIELDS:
        upload = request.FILES.get(field)
        error = _validar_imagem(upload)
        if error:
            image_errors[field] = [error]
            continue
        try:
            safe_files[field] = sanitized_image_upload(upload)
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
            image_errors[field] = ["Não foi possível preparar esta imagem."]
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
                "email": ["Use o mesmo email e o código privado para acompanhar o pedido."]
            },
        }, status=409)

    data = request.data.copy()
    if email:
        data["email"] = email

    form = PedidoEntradaForm(data, safe_files)
    if not form.is_valid():
        return Response({
            "detail": "Há alguns campos que precisam da sua atenção.",
            "errors": _normalizar_erros(form),
        }, status=400)

    pedido = form.save()
    codigo = str(pedido.token)

    return Response({
        "ok": True,
        "pedido_id": pedido.id,
        "codigo": codigo,
        "email": pedido.email,
        "message": (
            "Recebemos o seu pedido. Guarde este código privado para acompanhar "
            f"a análise: {codigo}"
        ),
    }, status=201)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
@throttle_classes([AccessStatusRateThrottle])
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

    pedido = PedidoEntrada.objects.filter(email__iexact=email, token=code).first()
    if not pedido:
        return Response(
            {"detail": "O email ou o código do pedido não está correto."},
            status=404,
        )

    return Response(_status_payload(pedido))
