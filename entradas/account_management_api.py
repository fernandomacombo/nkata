from datetime import timedelta

from django.contrib.auth import logout
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .account_state import refresh_temporary_pause
from .user_roles import member_profile_for_user


PAUSE_DURATIONS = {7, 30, 90}


def _state_payload(profile):
    return {
        "status": profile.status,
        "status_label": profile.get_status_display(),
        "user_paused": bool(profile.pausa_iniciada_pelo_usuario),
        "paused_until": profile.pausado_ate,
        "pause_reason": profile.motivo_pausa,
        "closure_requested_at": profile.encerramento_solicitado_em,
    }


@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def api_gestao_da_conta(request):
    profile = member_profile_for_user(request.user)
    if not profile:
        return Response({"detail": "Esta operação está disponível apenas para membros."}, status=403)

    profile = refresh_temporary_pause(profile)
    if request.method == "GET":
        return Response(_state_payload(profile))

    action = str(request.data.get("action", "")).strip().lower()
    reason = " ".join(str(request.data.get("reason", "")).split())[:500]

    if action == "pause":
        try:
            days = int(request.data.get("days", 0))
        except (TypeError, ValueError):
            days = 0
        if days not in PAUSE_DURATIONS:
            return Response({"days": ["Escolha 7, 30 ou 90 dias."]}, status=400)
        if not reason:
            return Response({"reason": ["Indique o motivo da pausa."]}, status=400)
        if profile.status != "ATIVO":
            return Response({"detail": "A conta não está disponível para uma nova pausa."}, status=400)

        profile.status = "PAUSADO"
        profile.visivel = False
        profile.destaque_publico = False
        profile.pausa_iniciada_pelo_usuario = True
        profile.pausado_ate = timezone.now() + timedelta(days=days)
        profile.motivo_pausa = reason[:240]
        profile.save(update_fields=[
            "status", "visivel", "destaque_publico",
            "pausa_iniciada_pelo_usuario", "pausado_ate", "motivo_pausa",
            "atualizado_em",
        ])
        return Response({
            "message": f"Conta suspensa durante {days} dias.",
            "state": _state_payload(profile),
        })

    if action == "reactivate":
        if profile.status != "PAUSADO" or not profile.pausa_iniciada_pelo_usuario:
            return Response({"detail": "Esta pausa só pode ser removida pela equipa NKATA."}, status=403)
        profile.status = "ATIVO"
        profile.visivel = True
        profile.pausa_iniciada_pelo_usuario = False
        profile.pausado_ate = None
        profile.motivo_pausa = ""
        profile.save(update_fields=[
            "status", "visivel", "pausa_iniciada_pelo_usuario",
            "pausado_ate", "motivo_pausa", "atualizado_em",
        ])
        return Response({
            "message": "Conta reativada.",
            "state": _state_payload(profile),
        })

    if action == "close":
        password = str(request.data.get("password", ""))
        if len(reason) < 5:
            return Response({"reason": ["Explique brevemente o motivo da eliminação."]}, status=400)
        if not password or not request.user.check_password(password):
            return Response({"password": ["A palavra-passe não está correta."]}, status=400)

        profile.status = "ENCERRAMENTO"
        profile.visivel = False
        profile.destaque_publico = False
        profile.pausa_iniciada_pelo_usuario = False
        profile.pausado_ate = None
        profile.motivo_pausa = ""
        profile.encerramento_solicitado_em = timezone.now()
        profile.motivo_encerramento = reason
        profile.save(update_fields=[
            "status", "visivel", "destaque_publico",
            "pausa_iniciada_pelo_usuario", "pausado_ate", "motivo_pausa",
            "encerramento_solicitado_em", "motivo_encerramento", "atualizado_em",
        ])
        type(request.user).objects.filter(pk=request.user.pk).update(is_active=False)
        logout(request)
        return Response({
            "message": "Pedido de eliminação registado. A conta foi desativada e será tratada pela equipa NKATA.",
            "signed_out": True,
        })

    return Response({"detail": "Ação de conta inválida."}, status=400)
