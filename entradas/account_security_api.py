from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


def password_change_errors(user, current_password, new_password, confirmation):
    errors = {}

    if not current_password:
        errors["current_password"] = ["Escreva a sua palavra-passe atual."]
    elif not user.check_password(current_password):
        errors["current_password"] = ["A palavra-passe atual não está correta."]

    if not new_password:
        errors["new_password"] = ["Escolha uma nova palavra-passe."]
    elif current_password and new_password == current_password:
        errors["new_password"] = ["A nova palavra-passe deve ser diferente da atual."]

    if new_password != confirmation:
        errors["confirmation"] = ["As palavras-passe não coincidem."]

    return errors


def _session_user_id(session):
    try:
        return str(session.get_decoded().get("_auth_user_id") or "")
    except Exception:
        return ""


def _user_sessions(user_id):
    expected = str(user_id)
    sessions = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if _session_user_id(session) == expected:
            sessions.append(session)
    return sessions


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_alterar_palavra_passe(request):
    current_password = str(request.data.get("current_password", ""))
    new_password = str(request.data.get("new_password", ""))
    confirmation = str(request.data.get("confirmation", ""))

    errors = password_change_errors(
        request.user,
        current_password,
        new_password,
        confirmation,
    )

    if errors:
        return Response(
            {
                "detail": "Revise os campos indicados.",
                "errors": errors,
            },
            status=400,
        )

    try:
        validate_password(new_password, user=request.user)
    except ValidationError as exc:
        return Response(
            {
                "detail": "Escolha uma palavra-passe mais segura.",
                "errors": {"new_password": list(exc.messages)},
            },
            status=400,
        )

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])

    # Evita terminar a sessão da pessoa depois da alteração da palavra-passe.
    update_session_auth_hash(request, request.user)

    return Response(
        {
            "ok": True,
            "message": "A sua palavra-passe foi atualizada com segurança.",
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_sessoes_da_conta(request):
    current_key = request.session.session_key
    sessions = _user_sessions(request.user.id)
    other_count = sum(1 for session in sessions if session.session_key != current_key)

    return Response(
        {
            "current": {
                "label": "Este dispositivo",
                "expires_at": request.session.get_expiry_date(),
            },
            "other_sessions": other_count,
            "total_sessions": len(sessions),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_terminar_outras_sessoes(request):
    current_key = request.session.session_key
    removed = 0

    for session in _user_sessions(request.user.id):
        if session.session_key == current_key:
            continue
        session.delete()
        removed += 1

    return Response(
        {
            "ok": True,
            "removed": removed,
            "message": (
                f"{removed} sessão(ões) encerrada(s). Este dispositivo continua ligado."
                if removed
                else "Não havia outras sessões abertas. Este dispositivo continua ligado."
            ),
        }
    )
