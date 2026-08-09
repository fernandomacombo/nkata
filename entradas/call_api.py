import json

from django.db import DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .call_models import ChamadaMatchNKATA, SinalChamadaNKATA
from .profile_media_api import profile_photo_url
from .models import MatchPerfil
from .plan_service import plan_for_user
from .webrtc_credentials import ice_servers_for_user


CALL_RING_TIMEOUT_SECONDS = 45
MAX_SIGNAL_PAYLOAD_CHARS = 65536
LIVE_CALL_STATES = {
    ChamadaMatchNKATA.ESTADO_CHAMANDO,
    ChamadaMatchNKATA.ESTADO_CONECTANDO,
    ChamadaMatchNKATA.ESTADO_ATIVA,
}


def _perfil_do_utilizador(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "perfil_nkata", None)


def _match_do_utilizador(user, match_id, *, for_update=False):
    perfil = _perfil_do_utilizador(user)
    if not perfil:
        return None

    qs = MatchPerfil.objects.filter(
        Q(perfil_1=perfil) | Q(perfil_2=perfil),
        id=match_id,
        status="ATIVO",
    ).select_related(
        "perfil_1",
        "perfil_1__usuario",
        "perfil_2",
        "perfil_2__usuario",
    )
    if for_update:
        qs = qs.select_for_update()
    return qs.first()


def _outro_utilizador(match, current_user):
    if match.perfil_1.usuario_id == current_user.id:
        return match.perfil_2.usuario
    if match.perfil_2.usuario_id == current_user.id:
        return match.perfil_1.usuario
    return None


def _feature_for_call_type(call_type):
    return "chat_video" if call_type == ChamadaMatchNKATA.TIPO_VIDEO else "chat_audio"


def _capability_available(user, call_type):
    feature = _feature_for_call_type(call_type)
    return bool(plan_for_user(user)["features"].get(feature, False))


def _purge_signals(call):
    if not call:
        return
    try:
        call.sinais.all().delete()
    except DatabaseError:
        pass


def _expire_ringing_call(call, now=None):
    if not call or call.estado != ChamadaMatchNKATA.ESTADO_CHAMANDO:
        return call
    now = now or timezone.now()
    age_seconds = (now - call.criada_em).total_seconds()
    if age_seconds <= CALL_RING_TIMEOUT_SECONDS:
        return call
    call.estado = ChamadaMatchNKATA.ESTADO_PERDIDA
    call.terminada_em = now
    call.save(update_fields=["estado", "terminada_em", "atualizada_em"])
    _purge_signals(call)
    return call


def _active_call_for_match(match):
    try:
        call = (
            ChamadaMatchNKATA.objects
            .filter(match=match, estado__in=LIVE_CALL_STATES)
            .select_related("iniciador")
            .order_by("-criada_em")
            .first()
        )
    except DatabaseError:
        return None
    return _expire_ringing_call(call)


def _active_call_for_user(user):
    perfil = _perfil_do_utilizador(user)
    if not perfil:
        return None
    try:
        call = (
            ChamadaMatchNKATA.objects
            .filter(
                Q(iniciador=user) | Q(match__perfil_1=perfil) | Q(match__perfil_2=perfil),
                estado__in=LIVE_CALL_STATES,
            )
            .select_related("iniciador")
            .order_by("-criada_em")
            .first()
        )
    except DatabaseError:
        return None
    return _expire_ringing_call(call)


def _serialize_call(call, request):
    if not call:
        return None
    return {
        "id": call.id,
        "match_id": call.match_id,
        "tipo": call.tipo,
        "estado": call.estado,
        "iniciador_id": call.iniciador_id,
        "iniciada_por_mim": call.iniciador_id == request.user.id,
        "recebida": call.iniciador_id != request.user.id,
        "criada_em": call.criada_em,
        "atendida_em": call.atendida_em,
        "terminada_em": call.terminada_em,
    }


def _serialize_signal(signal):
    return {
        "id": signal.id,
        "tipo": signal.tipo,
        "payload": signal.payload,
        "criado_em": signal.criado_em,
    }


def _call_setup_required_response():
    return Response(
        {
            "detail": "As chamadas NKATA ainda precisam de ser preparadas neste ambiente.",
            "setup_required": True,
        },
        status=503,
    )


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_chamada_match(request, match_id):
    match = _match_do_utilizador(request.user, match_id)
    if not match:
        return Response({"detail": "Conversa não encontrada."}, status=404)

    if request.method == "GET":
        since_signal_id = request.query_params.get("since_signal_id", "0")
        try:
            since_signal_id = max(0, int(since_signal_id or 0))
        except (TypeError, ValueError):
            since_signal_id = 0

        try:
            call = _active_call_for_match(match)
            signals = []
            if call and call.estado in LIVE_CALL_STATES:
                signals = [
                    _serialize_signal(signal)
                    for signal in call.sinais.filter(
                        id__gt=since_signal_id,
                    ).exclude(
                        remetente=request.user,
                    ).order_by("id")[:100]
                ]
        except DatabaseError:
            return _call_setup_required_response()

        return Response({
            "call": _serialize_call(call, request),
            "signals": signals,
            "ice_servers": ice_servers_for_user(request.user),
            "ring_timeout_seconds": CALL_RING_TIMEOUT_SECONDS,
            "setup_required": False,
        })

    action = str(request.data.get("action", "")).strip().lower()

    if action == "start":
        call_type = str(request.data.get("type", "")).strip().upper()
        if call_type not in {ChamadaMatchNKATA.TIPO_AUDIO, ChamadaMatchNKATA.TIPO_VIDEO}:
            return Response({"type": ["Escolha chamada de áudio ou vídeo."]}, status=400)

        if not _capability_available(request.user, call_type):
            return Response(
                {
                    "detail": "Chamadas estão disponíveis no NKATA Essencial e Premium.",
                    "code": "paid_plan_required_for_call",
                },
                status=403,
            )

        other_user = _outro_utilizador(match, request.user)
        if not other_user or not _capability_available(other_user, call_type):
            return Response(
                {
                    "detail": "Esta chamada não está disponível nesta ligação neste momento.",
                    "code": "call_unavailable_for_match",
                },
                status=409,
            )

        try:
            with transaction.atomic():
                locked_match = _match_do_utilizador(request.user, match_id, for_update=True)
                existing_match_call = _active_call_for_match(locked_match)
                existing_user_call = _active_call_for_user(request.user)
                existing_other_call = _active_call_for_user(other_user)
                existing = existing_match_call or existing_user_call or existing_other_call
                if existing and existing.estado in LIVE_CALL_STATES:
                    return Response(
                        {
                            "detail": "Uma das pessoas já está numa chamada. Tente novamente daqui a pouco.",
                            "code": "participant_already_in_call",
                        },
                        status=409,
                    )
                call = ChamadaMatchNKATA.objects.create(
                    match=locked_match,
                    iniciador=request.user,
                    tipo=call_type,
                    estado=ChamadaMatchNKATA.ESTADO_CHAMANDO,
                )
        except DatabaseError:
            return _call_setup_required_response()

        return Response({
            "call": _serialize_call(call, request),
            "signals": [],
            "ice_servers": ice_servers_for_user(request.user),
        }, status=201)

    try:
        call_id = int(request.data.get("call_id", 0) or 0)
    except (TypeError, ValueError):
        call_id = 0

    if not call_id:
        return Response({"call_id": ["Chamada inválida."]}, status=400)

    try:
        call = ChamadaMatchNKATA.objects.select_related("iniciador").filter(
            id=call_id,
            match=match,
        ).first()
    except DatabaseError:
        return _call_setup_required_response()

    if not call:
        return Response({"detail": "Chamada não encontrada."}, status=404)

    call = _expire_ringing_call(call)

    if action == "signal":
        if call.estado not in LIVE_CALL_STATES:
            return Response({"detail": "Esta chamada já terminou."}, status=409)

        signal_type = str(request.data.get("signal_type", "")).strip().upper()
        if signal_type not in {
            SinalChamadaNKATA.TIPO_OFFER,
            SinalChamadaNKATA.TIPO_ANSWER,
            SinalChamadaNKATA.TIPO_ICE,
        }:
            return Response({"signal_type": ["Sinal WebRTC inválido."]}, status=400)

        if signal_type == SinalChamadaNKATA.TIPO_OFFER and call.iniciador_id != request.user.id:
            return Response({"detail": "Apenas o iniciador pode enviar a oferta."}, status=403)
        if signal_type == SinalChamadaNKATA.TIPO_ANSWER and call.iniciador_id == request.user.id:
            return Response({"detail": "A resposta deve vir da outra pessoa."}, status=403)

        payload = request.data.get("payload")
        if not isinstance(payload, dict):
            return Response({"payload": ["Payload WebRTC inválido."]}, status=400)
        if len(json.dumps(payload, ensure_ascii=False)) > MAX_SIGNAL_PAYLOAD_CHARS:
            return Response({"payload": ["Sinal WebRTC demasiado grande."]}, status=400)

        try:
            signal = SinalChamadaNKATA.objects.create(
                chamada=call,
                remetente=request.user,
                tipo=signal_type,
                payload=payload,
            )
        except DatabaseError:
            return _call_setup_required_response()

        return Response({"signal": _serialize_signal(signal)}, status=201)

    now = timezone.now()

    if action == "accept":
        if call.iniciador_id == request.user.id:
            return Response({"detail": "O iniciador não pode atender a própria chamada."}, status=403)
        if call.estado != ChamadaMatchNKATA.ESTADO_CHAMANDO:
            return Response({"detail": "Esta chamada já não pode ser atendida."}, status=409)
        if not _capability_available(request.user, call.tipo):
            return Response(
                {"detail": "O seu plano atual não permite esta chamada."},
                status=403,
            )
        # Atender apenas inicia a negociação. O cronómetro real começa quando
        # a ligação WebRTC reporta connectionState=connected (action=active).
        call.estado = ChamadaMatchNKATA.ESTADO_CONECTANDO
        call.save(update_fields=["estado", "atualizada_em"])

    elif action == "active":
        if call.estado not in {
            ChamadaMatchNKATA.ESTADO_CHAMANDO,
            ChamadaMatchNKATA.ESTADO_CONECTANDO,
            ChamadaMatchNKATA.ESTADO_ATIVA,
        }:
            return Response({"detail": "Esta chamada já terminou."}, status=409)
        if call.estado != ChamadaMatchNKATA.ESTADO_ATIVA:
            call.estado = ChamadaMatchNKATA.ESTADO_ATIVA
            if not call.atendida_em:
                call.atendida_em = now
            call.save(update_fields=["estado", "atendida_em", "atualizada_em"])

    elif action == "decline":
        if call.iniciador_id == request.user.id:
            return Response({"detail": "Use terminar para cancelar a chamada."}, status=403)
        if call.estado not in {
            ChamadaMatchNKATA.ESTADO_CHAMANDO,
            ChamadaMatchNKATA.ESTADO_CONECTANDO,
        }:
            return Response({"detail": "Esta chamada já terminou."}, status=409)
        call.estado = ChamadaMatchNKATA.ESTADO_RECUSADA
        call.terminada_em = now
        call.save(update_fields=["estado", "terminada_em", "atualizada_em"])
        _purge_signals(call)

    elif action in {"end", "failed"}:
        if call.estado not in LIVE_CALL_STATES:
            _purge_signals(call)
            return Response({"call": _serialize_call(call, request)})

        if action == "failed":
            call.estado = ChamadaMatchNKATA.ESTADO_FALHOU
        elif (
            call.estado == ChamadaMatchNKATA.ESTADO_CHAMANDO
            and call.iniciador_id == request.user.id
            and not call.atendida_em
        ):
            # O chamador desligou antes de haver ligação: para quem recebeu,
            # isto deve aparecer como chamada perdida; para quem ligou, como
            # não atendida.
            call.estado = ChamadaMatchNKATA.ESTADO_PERDIDA
        else:
            call.estado = ChamadaMatchNKATA.ESTADO_TERMINADA

        call.terminada_em = now
        call.save(update_fields=["estado", "terminada_em", "atualizada_em"])
        _purge_signals(call)

    else:
        return Response({"action": ["Ação de chamada inválida."]}, status=400)

    return Response({"call": _serialize_call(call, request)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def api_chamada_recebida(request):
    perfil = _perfil_do_utilizador(request.user)
    if not perfil:
        return Response({"call": None, "setup_required": False})

    try:
        calls = (
            ChamadaMatchNKATA.objects
            .filter(
                Q(match__perfil_1=perfil) | Q(match__perfil_2=perfil),
                estado=ChamadaMatchNKATA.ESTADO_CHAMANDO,
            )
            .exclude(iniciador=request.user)
            .select_related(
                "iniciador",
                "match",
                "match__perfil_1",
                "match__perfil_1__pedido",
                "match__perfil_2",
                "match__perfil_2__pedido",
            )
            .order_by("-criada_em")
        )
        call = calls.first()
        call = _expire_ringing_call(call)
        if not call or call.estado != ChamadaMatchNKATA.ESTADO_CHAMANDO:
            return Response({"call": None, "setup_required": False})

        caller_profile = (
            call.match.perfil_1
            if call.match.perfil_1.usuario_id == call.iniciador_id
            else call.match.perfil_2
        )
        foto_url = profile_photo_url(caller_profile)
        return Response({
            "call": {
                **_serialize_call(call, request),
                "caller": {
                    "id": caller_profile.id,
                    "nome_publico": caller_profile.nome_publico,
                    "cidade": caller_profile.cidade,
                    "foto_url": foto_url,
                },
            },
            "setup_required": False,
        })
    except DatabaseError:
        return Response({"call": None, "setup_required": True})
