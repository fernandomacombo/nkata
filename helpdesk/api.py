from django.shortcuts import get_object_or_404
from entradas.branded_email import send_branded_email
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from .models import SupportTicket, SupportReply


class GuestSupportThrottle(AnonRateThrottle):
    scope = "support_guest"
    rate = "3/hour"


class MemberSupportThrottle(UserRateThrottle):
    scope = "support_member"
    rate = "10/hour"


def serialize_ticket(ticket):
    return {
        "id": str(ticket.id), "category": ticket.category,
        "subject": ticket.subject, "status": ticket.status,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
        "replies": [{"body": reply.body, "created_at": reply.created_at.isoformat()} for reply in ticket.replies.all()],
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([GuestSupportThrottle, MemberSupportThrottle])
def tickets(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return Response({"detail": "Inicie sessão para consultar os seus pedidos."}, status=status.HTTP_401_UNAUTHORIZED)
        items = SupportTicket.objects.filter(user=request.user).prefetch_related('replies')[:50]
        return Response({"results": [serialize_ticket(item) for item in items]})

    data = request.data
    category = str(data.get("category", "")).strip()
    subject = str(data.get("subject", "")).strip()
    description = str(data.get("description", "")).strip()
    # For logged-in accounts the email is server-derived, never trusted from client data.
    email = request.user.email if request.user.is_authenticated else str(data.get("email", "")).strip()
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
    except ValidationError:
        return Response({"detail": "Indique um email válido."}, status=400)
    if category not in SupportTicket.Category.values:
        return Response({"detail": "Selecione uma categoria válida."}, status=400)
    if not (5 <= len(subject) <= 140) or not (15 <= len(description) <= 4000):
        return Response({"detail": "Assunto: 5–140 caracteres. Descrição: 15–4000 caracteres."}, status=400)
    if not email:
        return Response({"detail": "Indique um email válido."}, status=400)
    ticket = SupportTicket.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email=email, category=category, subject=subject, description=description,
    )
    # Best-effort acknowledgment: a mail outage must never discard a saved ticket.
    # The reference is not an authentication credential and grants no access to history.
    try:
        send_branded_email(
            subject="NKATA · Recebemos o seu pedido de ajuda",
            body=(
                "Olá,\n\nRecebemos o seu pedido de suporte.\n"
                f"Referência: {ticket.id}\n"
                "A nossa equipa analisará o assunto.\n\n"
                "Se não pediu ajuda, pode ignorar esta mensagem.\nNKATA"
            ),
            recipient=ticket.email,
            title="Pedido de ajuda recebido",
            greeting="Olá,",
            paragraphs=[
                "Recebemos o seu pedido de suporte.",
                f"Referência: {ticket.id}",
                "A nossa equipa analisará o assunto. Não envie palavras-passe nem fotografias do BI por email.",
            ],
            notice="Esta referência identifica o pedido, mas não permite consultar dados privados.",
            fail_silently=True,
        )
    except Exception:
        # Logged out guest still receives the reference in the HTTP response.
        pass
    return Response({"id": str(ticket.id), "detail": "Pedido recebido. Guarde esta referência."}, status=201)


def _support_admin(request):
    return bool(request.user.is_authenticated and request.user.is_active and request.user.is_superuser)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def admin_tickets(request):
    if not _support_admin(request):
        return Response({"detail": "Apenas o administrador principal pode consultar os pedidos."}, status=403)
    items = SupportTicket.objects.prefetch_related("replies").all()[:100]
    return Response({"results": [
        {**serialize_ticket(item), "email": item.email, "description": item.description}
        for item in items
    ]})


@api_view(["POST"])
@permission_classes([permissions.IsAdminUser])
@throttle_classes([MemberSupportThrottle])
def admin_reply(request, ticket_id):
    if not _support_admin(request):
        return Response({"detail": "Sem autorização para responder a pedidos."}, status=403)
    body = str(request.data.get("body", "")).strip()
    new_status = str(request.data.get("status", "aguarda_resposta")).strip()
    if not (5 <= len(body) <= 4000):
        return Response({"detail": "A resposta deve ter entre 5 e 4000 caracteres."}, status=400)
    if new_status not in SupportTicket.Status.values:
        return Response({"detail": "Estado inválido."}, status=400)
    ticket = get_object_or_404(SupportTicket, pk=ticket_id)
    # Não guardamos respostas como enviadas se o backend não confirmar o email.
    try:
        sent = send_branded_email(
            subject=f"NKATA · Resposta ao pedido {str(ticket.id)[:8]}",
            body="Olá,\n\n" + body + "\n\nEquipa de Suporte NKATA",
            recipient=ticket.email,
            title="Resposta ao seu pedido",
            greeting="Olá,",
            paragraphs=[body],
            notice="Esta resposta refere-se a um pedido de suporte feito ao NKATA.",
            fail_silently=False,
        )
    except Exception:
        return Response({"detail": "Não foi possível enviar o email. A resposta não foi registada."}, status=503)
    if sent != 1:
        return Response({"detail": "O serviço de email não confirmou o envio."}, status=503)
    SupportReply.objects.create(ticket=ticket, staff=request.user, body=body)
    ticket.status = new_status
    ticket.save(update_fields=["status", "updated_at"])
    return Response({"detail": "Resposta enviada.", "ticket": serialize_ticket(ticket)})
