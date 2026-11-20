"""Private operational dossier for one NKATA member.

Only administrators with the 'members' capability can view it. This endpoint is
read-only, does not expose identity scans, passwords, message text or secrets,
and never changes account or payment records.
"""
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .identity_models import pedido_tem_identidade_verificada, VerificacaoIdentidadeNKATA
from .models import (
    AcaoPerfil, DenunciaPerfil, MatchPerfil, MensagemMatch,
    PedidoPagamentoNKATA, PerfilNKATA,
)
from .moments_models import MomentoNKATA
from .posts_models import PublicacaoNKATA
from .plan_service import PLAN_DEFINITIONS, plan_code_for_user
from .profile_media_api import profile_photo_url
from .user_roles import has_admin_capability


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def api_admin_member_dossier(request, profile_id):
    if not request.user.is_active or not has_admin_capability(request.user, "members"):
        return Response({"detail": "Sem permissão para consultar a ficha do membro."}, status=403)

    profile = (
        PerfilNKATA.objects
        .select_related("pedido", "usuario")
        .filter(pk=profile_id, usuario__is_staff=False)
        .first()
    )
    if not profile:
        return Response({"detail": "Membro não encontrado."}, status=404)
    pedido, user = profile.pedido, profile.usuario
    verification = VerificacaoIdentidadeNKATA.objects.filter(pedido=pedido).first()
    plan_code = plan_code_for_user(user) if user else "LIVRE"
    entitlement = getattr(user, "acesso_plano_nkata", None) if user else None
    match_filter = Q(perfil_1=profile) | Q(perfil_2=profile)
    matches = MatchPerfil.objects.filter(match_filter)
    payments = PedidoPagamentoNKATA.objects.filter(usuario=user) if user else PedidoPagamentoNKATA.objects.none()
    logs = (
        LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(profile),
            object_id=str(profile.pk),
        ).select_related("user").order_by("-action_time")[:15]
    )

    return Response({
        "member": {
            "id": profile.pk,
            "name": profile.nome_publico,
            "photo_url": profile_photo_url(profile),
            "city": profile.cidade,
            "age": profile.idade,
            "objective": profile.get_objetivo_display(),
            "email": pedido.email,
            "phone": pedido.telefone,
            "registered_at": profile.criado_em,
            "account_active": bool(user and user.is_active),
            "status": profile.status,
            "status_label": profile.get_status_display(),
            "visible": profile.visivel,
            "public_presentation_enabled": profile.destaque_publico,
            "public_photo_approved": profile.foto_destaque_publico_aprovada,
            "about": profile.sobre_si,
            "values": profile.o_que_valoriza,
            "boundaries": profile.o_que_nao_aceita,
        },
        "identity": {
            "entry_status": pedido.status,
            "entry_status_label": pedido.get_status_display(),
            "nkata_id_status": verification.status if verification else ("POR_INICIAR" if pedido.verificacao_apos_entrada else "LEGADO"),
            "nkata_id_label": verification.get_status_display() if verification else ("Por iniciar" if pedido.verificacao_apos_entrada else "Verificação anterior"),
            "captures_complete": bool(verification and verification.capturas_completas),
            "confirmed": bool(pedido_tem_identidade_verificada(pedido)),
            "document_confirmed": bool(pedido.documento_confirmado),
            "risk": verification.risco if verification else "INDEFINIDO",
        },
        "subscription": {
            "code": plan_code,
            "label": PLAN_DEFINITIONS.get(plan_code, PLAN_DEFINITIONS["LIVRE"])["label"],
            "starts_at": entitlement.inicio if entitlement else None,
            "expires_at": entitlement.fim if entitlement else None,
            "origin": entitlement.origem if entitlement else None,
        },
        "activity": {
            "matches": matches.count(),
            "active_matches": matches.filter(status="ATIVO").count(),
            "interests_sent": AcaoPerfil.objects.filter(usuario=user, tipo="INTERESSE").count() if user else 0,
            "followers": AcaoPerfil.objects.filter(perfil=profile, tipo="SEGUIR").count(),
            "messages_sent": MensagemMatch.objects.filter(remetente=user).count() if user else 0,
            "posts": PublicacaoNKATA.objects.filter(perfil=profile).count(),
            "posts_pending": PublicacaoNKATA.objects.filter(perfil=profile, moderacao_status="PENDENTE").count(),
            "moments": MomentoNKATA.objects.filter(perfil=profile).count(),
            "moments_pending": MomentoNKATA.objects.filter(perfil=profile, moderacao_status="PENDENTE").count(),
            "reports_pending": DenunciaPerfil.objects.filter(perfil=profile, analisada=False).count(),
            "reports_total": DenunciaPerfil.objects.filter(perfil=profile).count(),
        },
        "payments": {
            "total": payments.count(),
            "successful": payments.filter(estado="PAGO").count(),
            "recent": [
                {
                    "reference": payment.referencia,
                    "product": payment.produto,
                    "amount": str(payment.valor),
                    "currency": payment.moeda,
                    "status": payment.estado,
                    "created_at": payment.criado_em,
                }
                for payment in payments.order_by("-criado_em")[:8]
            ],
        },
        "audit": [
            {
                "date": entry.action_time,
                "operator": entry.user.get_username() if entry.user_id else "Sistema",
                "description": entry.change_message,
            }
            for entry in logs
        ],
    })
