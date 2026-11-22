from django.db import DatabaseError
from django.db.models import DurationField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .call_models import ChamadaMatchNKATA
from .chat_media_models import MensagemAudioMatchNKATA
from .models import AcaoPerfil, MatchPerfil, MensagemMatch
from .plan_service import plan_for_user, signal_quota_for_user
from .posts_models import PublicacaoNKATA
from .user_roles import member_profile_for_user


def _profile_completeness(perfil):
    checks = [
        bool(perfil.foto_principal),
        bool(str(perfil.nome_publico or "").strip()),
        bool(str(perfil.cidade or "").strip()),
        bool(str(perfil.objetivo or "").strip()),
        bool(str(perfil.sobre_si or "").strip()),
        bool(str(perfil.o_que_valoriza or "").strip()),
        bool(str(perfil.o_que_nao_aceita or "").strip()),
    ]
    return round((sum(checks) / len(checks)) * 100)


def _publication_stats(perfil):
    try:
        publications = PublicacaoNKATA.objects.filter(perfil=perfil)
        return {
            "approved": publications.filter(moderacao_status="APROVADO").count(),
            "pending": publications.filter(moderacao_status="PENDENTE").count(),
        }
    except DatabaseError:
        return {"approved": 0, "pending": 0}


def _message_count(user):
    total = MensagemMatch.objects.filter(remetente=user).count()
    try:
        total += MensagemAudioMatchNKATA.objects.filter(remetente=user).count()
    except DatabaseError:
        pass
    return total


def _call_stats(user, match_ids):
    empty = {"total": 0, "completed": 0, "duration_seconds": 0}
    if not match_ids:
        return empty

    try:
        calls = ChamadaMatchNKATA.objects.filter(match_id__in=match_ids)
        completed = calls.filter(
            estado=ChamadaMatchNKATA.ESTADO_TERMINADA,
            atendida_em__isnull=False,
            terminada_em__isnull=False,
        )
        duration = completed.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("terminada_em") - F("atendida_em"),
                    output_field=DurationField(),
                )
            )
        )["total"]
        return {
            "total": calls.count(),
            "completed": completed.count(),
            "duration_seconds": max(0, int(duration.total_seconds())) if duration else 0,
        }
    except DatabaseError:
        return empty


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_resumo_da_conta(request):
    perfil = member_profile_for_user(request.user)
    if not perfil:
        return Response({"detail": "Perfil não encontrado."}, status=404)

    matches = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        status="ATIVO",
    )
    match_ids = list(matches.values_list("id", flat=True))
    plan = plan_for_user(request.user)
    quota = signal_quota_for_user(request.user)
    publications = _publication_stats(perfil)

    return Response({
        "updated_at": timezone.now(),
        "profile": {
            "status": perfil.status,
            "status_label": perfil.get_status_display(),
            "visible": perfil.visivel,
            "verified": getattr(perfil.pedido, "status", "") == "APROVADO",
            "completeness": _profile_completeness(perfil),
            "public_preview": perfil.destaque_publico,
            "public_impressions": perfil.destaque_publico_exibicoes,
            "has_cover": bool(perfil.capa_publicacao_id),
        },
        "plan": {
            "code": plan["code"],
            "label": plan["label"],
            "paid": plan["paid"],
            "signal_quota": quota,
        },
        "performance": {
            "active_matches": len(match_ids),
            "interests_received": AcaoPerfil.objects.filter(
                perfil=perfil,
                tipo="INTERESSE",
            ).count(),
            "followers": AcaoPerfil.objects.filter(
                perfil=perfil,
                tipo="SEGUIR",
            ).count(),
            "saved_by_members": AcaoPerfil.objects.filter(
                perfil=perfil,
                tipo="GUARDADO",
            ).count(),
            "public_impressions": perfil.destaque_publico_exibicoes,
        },
        "activity": {
            "approved_publications": publications["approved"],
            "pending_publications": publications["pending"],
            "messages_sent": _message_count(request.user),
            "calls": _call_stats(request.user, match_ids),
        },
    })
