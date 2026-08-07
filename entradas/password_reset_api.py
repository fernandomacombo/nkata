from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response


User = get_user_model()
GENERIC_RESET_MESSAGE = (
    "Se existir uma conta associada a este email, receberá as instruções para criar uma nova palavra-passe."
)


def _user_from_reset_link(uidb64):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.filter(pk=uid, is_active=True).first()
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return None


def _reset_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    frontend = settings.NKATA_FRONTEND_URL.rstrip("/")
    return f"{frontend}/nova-senha/{uid}/{token}/"


def _send_reset_email(user):
    link = _reset_link(user)
    first_name = (user.first_name or user.username or "Olá").strip().split()[0]
    subject = "Recupere o acesso à sua conta NKATA"
    body = (
        f"Olá {first_name},\n\n"
        "Recebemos um pedido para criar uma nova palavra-passe para a sua conta NKATA.\n\n"
        f"Criar nova palavra-passe:\n{link}\n\n"
        "Por segurança, este link é temporário e deixa de funcionar depois de a palavra-passe ser alterada.\n"
        "Se não pediu esta alteração, pode ignorar este email.\n\n"
        "NKATA\nRelações sérias começam com intenções claras."
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def api_pedir_recuperacao_senha(request):
    email = str(request.data.get("email", "")).strip().lower()

    if email:
        user = (
            User.objects
            .filter(email__iexact=email, is_active=True)
            .order_by("id")
            .first()
        )
        if user and user.has_usable_password():
            _send_reset_email(user)

    # A resposta é deliberadamente idêntica para emails existentes e inexistentes.
    return Response({"ok": True, "message": GENERIC_RESET_MESSAGE})


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def api_confirmar_recuperacao_senha(request, uidb64, token):
    user = _user_from_reset_link(uidb64)
    valid = bool(user and default_token_generator.check_token(user, token))

    if request.method == "GET":
        if not valid:
            return Response(
                {"valid": False, "detail": "Este link de recuperação já não é válido."},
                status=400,
            )
        return Response({"valid": True})

    if not valid:
        return Response(
            {"detail": "Este link de recuperação já não é válido."},
            status=400,
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

    return Response({
        "ok": True,
        "message": "A sua palavra-passe foi atualizada. Já pode entrar no NKATA.",
    })
