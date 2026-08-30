from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .call_api import _expire_ringing_call
from .call_models import ChamadaMatchNKATA
from .models import MatchPerfil
from .user_roles import active_member_profile_for_user


MAX_CALL_HISTORY_ITEMS = 40


def _perfil_do_utilizador(user):
    return active_member_profile_for_user(user)


def _match_do_utilizador(user, match_id):
    perfil = _perfil_do_utilizador(user)
    if not perfil:
        return None
    return MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        id=match_id,
    ).first()


def _duration_seconds(call):
    if not call.atendida_em:
        return 0
    end = call.terminada_em
    if not end and call.estado == ChamadaMatchNKATA.ESTADO_ATIVA:
        end = timezone.now()
    if not end:
        return 0
    return max(0, int((end - call.atendida_em).total_seconds()))


def _status_label(call, user_id):
    outgoing = call.iniciador_id == user_id
    if call.estado == ChamadaMatchNKATA.ESTADO_PERDIDA:
        return "Chamada não atendida" if outgoing else "Chamada perdida"
    if call.estado == ChamadaMatchNKATA.ESTADO_RECUSADA:
        return "Chamada recusada"
    if call.estado == ChamadaMatchNKATA.ESTADO_FALHOU:
        return "Chamada não concluída"
    if call.estado == ChamadaMatchNKATA.ESTADO_CHAMANDO:
        return "A chamar" if outgoing else "Chamada recebida"
    if call.estado == ChamadaMatchNKATA.ESTADO_CONECTANDO:
        return "A conectar"
    if call.estado == ChamadaMatchNKATA.ESTADO_ATIVA:
        return "Chamada em curso"
    if call.estado == ChamadaMatchNKATA.ESTADO_TERMINADA and not call.atendida_em:
        return "Chamada cancelada" if outgoing else "Chamada perdida"
    return "Chamada terminada"


def serialize_call_history(call, user_id):
    outgoing = call.iniciador_id == user_id
    missed = bool(
        not outgoing
        and not call.atendida_em
        and call.estado in {
            ChamadaMatchNKATA.ESTADO_PERDIDA,
            ChamadaMatchNKATA.ESTADO_TERMINADA,
        }
    )
    return {
        "id": call.id,
        "match_id": call.match_id,
        "type": call.tipo,
        "type_label": call.get_tipo_display(),
        "state": call.estado,
        "status_label": _status_label(call, user_id),
        "direction": "OUTGOING" if outgoing else "INCOMING",
        "missed": missed,
        "duration_seconds": _duration_seconds(call),
        "created_at": call.criada_em,
        "answered_at": call.atendida_em,
        "ended_at": call.terminada_em,
        "activity_at": call.terminada_em or call.atualizada_em or call.criada_em,
    }


def serialize_call_message(call, user_id):
    item = serialize_call_history(call, user_id)
    return {
        "id": f"call-{item['id']}",
        "match": item["match_id"],
        "tipo": "CALL",
        "call_id": item["id"],
        "call_type": item["type"],
        "call_state": item["state"],
        "call_label": item["status_label"],
        "call_direction": item["direction"],
        "call_missed": item["missed"],
        "duracao_segundos": item["duration_seconds"],
        "texto": item["status_label"],
        "lida": True,
        "minha": item["direction"] == "OUTGOING",
        "criado_em": item["activity_at"],
    }


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_historico_chamadas_match(request, match_id):
    match = _match_do_utilizador(request.user, match_id)
    if not match:
        return Response({"detail": "Conversa não encontrada."}, status=404)

    try:
        calls = list(
            ChamadaMatchNKATA.objects
            .filter(match=match)
            .order_by("-criada_em")[:MAX_CALL_HISTORY_ITEMS]
        )
        calls = [_expire_ringing_call(call) for call in calls]
    except DatabaseError:
        return Response({
            "results": [],
            "setup_required": True,
        })

    return Response({
        "results": [serialize_call_history(call, request.user.id) for call in calls],
        "setup_required": False,
    })
