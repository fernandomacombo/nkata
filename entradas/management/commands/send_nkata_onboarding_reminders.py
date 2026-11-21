from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ...branded_email import send_branded_email
from ...models import PedidoEntrada


def next_step(pedido):
    if pedido.status == "PRECISA_CORRIGIR":
        return ("O seu pedido precisa de uma correção. Consulte as instruções da equipa.",
                "/acompanhar-pedido/")
    if pedido.status != "APROVADO":
        return None

    perfil = getattr(pedido, "perfil", None)
    if not hasattr(pedido, "questionario"):
        return ("A sua entrada foi aprovada. Preencha o questionário e crie a sua palavra-passe.",
                f"/questionario/{pedido.token}/")
    if not perfil or not perfil.usuario or not perfil.usuario.has_usable_password():
        return ("O questionário foi recebido. Crie a sua palavra-passe para entrar.",
                f"/questionario/{pedido.token}/")
    if perfil.status == "BLOQUEADO" or not perfil.usuario.is_active:
        return None

    verification = getattr(pedido, "verificacao_identidade", None)
    if verification and verification.status == "REVISAO":
        return None
    if pedido.documento_confirmado or not pedido.verificacao_apos_entrada:
        return None
    if verification and verification.status == "REPETIR":
        message = "A equipa solicitou novas capturas. Entre no NKATA, abra Matches e siga as instruções do NKATA ID."
    else:
        message = "A sua conta já está criada. Entre, abra Matches e conclua o NKATA ID para desbloquear as funções que exigem identidade verificada."
    return message, "/matches/"


class Command(BaseCommand):
    help = "Envia lembretes relativos aos três dias após a aprovação ou a receção do pedido."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        start = now - timedelta(days=4)
        latest = now - timedelta(days=1)
        candidates = PedidoEntrada.objects.filter(
            Q(status="APROVADO", onboarding_aprovado_em__gt=start, onboarding_aprovado_em__lte=latest)
            | Q(status="PRECISA_CORRIGIR", criado_em__gt=start, criado_em__lte=latest)
        ).values_list("pk", flat=True)

        sent = eligible = 0
        for pk in candidates.iterator():
            with transaction.atomic():
                pedido = PedidoEntrada.objects.select_for_update().get(pk=pk)
                anchor = (pedido.onboarding_aprovado_em if pedido.status == "APROVADO"
                          else pedido.criado_em)
                if not anchor or not start < anchor <= latest:
                    continue
                day = (now - anchor).days
                if pedido.onboarding_lembrete_em and (now - pedido.onboarding_lembrete_em < timedelta(hours=23)
                    or pedido.onboarding_lembrete_em >= anchor + timedelta(days=day)):
                    continue
                step = next_step(pedido)
                if not step:
                    continue

                eligible += 1
                if options["dry_run"]:
                    continue
                message, path = step
                url = settings.NKATA_FRONTEND_URL.rstrip("/") + path
                subject = "Continue o seu registo no NKATA"
                benefit = (
                    "O NKATA é uma comunidade para relações sérias. O registo completo "
                    "e a verificação de identidade ajudam a proteger os membros e a reduzir perfis falsos."
                )
                greeting = f"Olá, {pedido.nome_completo.split()[0] if pedido.nome_completo.strip() else 'membro'}."
                if send_branded_email(
                    subject=subject, title=subject, recipient=pedido.email, greeting=greeting,
                    body=f"{greeting}\n\n{message}\n\n{benefit}\n\nContinuar no NKATA: {url}",
                    paragraphs=[message, benefit], action_label="Continuar no NKATA", action_url=url,
                ):
                    PedidoEntrada.objects.filter(pk=pk).update(onboarding_lembrete_em=now)
                    sent += 1

        self.stdout.write(f"Lembretes elegíveis: {eligible}. Enviados: {sent}.")
