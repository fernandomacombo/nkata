from django.utils import timezone

from .models import PerfilNKATA


def refresh_temporary_pause(profile):
    if not profile or profile.status != "PAUSADO":
        return profile
    if not profile.pausa_iniciada_pelo_usuario or not profile.pausado_ate:
        return profile
    if profile.pausado_ate > timezone.now():
        return profile

    PerfilNKATA.objects.filter(pk=profile.pk).update(
        status="ATIVO",
        visivel=True,
        pausa_iniciada_pelo_usuario=False,
        pausado_ate=None,
        motivo_pausa="",
    )
    profile.status = "ATIVO"
    profile.visivel = True
    profile.pausa_iniciada_pelo_usuario = False
    profile.pausado_ate = None
    profile.motivo_pausa = ""
    return profile
