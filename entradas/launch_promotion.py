from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import AcessoPlanoNKATA, PromocaoLancamentoNKATA


@transaction.atomic
def complete_registration_password(user, password):
    """Return whether the password was created and a launch place was granted."""
    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    if user.has_usable_password():
        return False, False

    user.set_password(password)
    user.save(update_fields=["password"])
    now = timezone.now()
    if settings.NKATA_CREDIT_TRANSITION_ENABLED:
        return True, False
    if not user.is_active or AcessoPlanoNKATA.objects.filter(usuario=user, fim__gt=now).exists():
        return True, False

    campaign, _ = PromocaoLancamentoNKATA.objects.get_or_create(codigo="lancamento-15-dias")
    claimed = PromocaoLancamentoNKATA.objects.filter(
        pk=campaign.pk, vagas_atribuidas__lt=100,
    ).update(vagas_atribuidas=F("vagas_atribuidas") + 1)
    if not claimed:
        return True, False

    AcessoPlanoNKATA.objects.update_or_create(
        usuario=user,
        defaults={
            "plano": "QUINZENAL",
            "inicio": now,
            "fim": now + timedelta(days=15),
            "origem": "PROMO_LANCAMENTO",
        },
    )
    return True, True
