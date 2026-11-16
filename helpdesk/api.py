from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from .models import SupportTicket


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
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([GuestSupportThrottle, MemberSupportThrottle])
def tickets(request):
    if request.method == "GET":
        if not request.user.is_authenticated:
            return Response({"detail": "Inicie sessão para consultar os seus pedidos."}, status=status.HTTP_401_UNAUTHORIZED)
        items = SupportTicket.objects.filter(user=request.user)[:50]
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
    # Do not expose a guest's ticket history with only an email address or a guessed ID.
    return Response({"id": str(ticket.id), "detail": "Pedido recebido. Guarde esta referência."}, status=201)
