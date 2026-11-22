from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ...branded_email import send_branded_email
from ...identity_models import pedido_tem_identidade_verificada
from ...models import PedidoEntrada


def next_step(pedido):
    if pedido.status == "PRECISA_CORRIGIR":
        return ("Corrija o seu pedido de acesso ao NKATA",
                "O seu pedido precisa de uma correção. Consulte as instruções da equipa.",
                "/acompanhar-pedido/")
    if pedido.status != "APROVADO":
        return None

    perfil = getattr(pedido, "perfil", None)
    if not hasattr(pedido, "questionario"):
        return ("Conclua o questionário e crie a sua palavra-passe",
                "O seu pedido de acesso foi aprovado. O questionário ajuda a completar o seu perfil "
                "e a apresentar o que procura a pessoas com intenções semelhantes. "
                "Depois de responder, crie a sua palavra-passe para entrar na conta.",
                f"/questionario/{pedido.token}/")
    if not perfil or not perfil.usuario or not perfil.usuario.has_usable_password():
        return ("Crie a sua palavra-passe para entrar no NKATA",
                "As suas respostas já foram guardadas. Crie uma palavra-passe para proteger a sua conta e poder entrar no NKATA.",
                f"/questionario/{pedido.token}/")
    if perfil.status in {"BLOQUEADO", "ENCERRAMENTO"} or not perfil.usuario.is_active:
        return None

    verification = getattr(pedido, "verificacao_identidade", None)
    if verification and verification.status == "REVISAO":
        return None
    if pedido_tem_identidade_verificada(pedido):
        return None
    if verification and verification.status == "REPETIR":
        message = "A equipa solicitou novas capturas. Entre no NKATA, abra Matches e siga as instruções do NKATA ID."
    else:
        message = "A sua conta já está criada. Entre, abra Matches e conclua o NKATA ID para desbloquear as funções que exigem identidade verificada."
    message += (
        " O NKATA ID faz parte da segurança da comunidade. A confirmação da identidade "
        "ajuda a reduzir perfis falsos e a proteger quem usa o NKATA."
    )
    return "Conclua a verificação de identidade no NKATA", message, "/matches/"


class Command(BaseCommand):
    help = "Envia lembretes nos primeiros três dias e recupera um primeiro aviso em atraso."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        start = now - timedelta(days=4)
        latest = now - timedelta(days=1)
        candidates = PedidoEntrada.objects.filter(
            Q(status="APROVADO", onboarding_aprovado_em__lte=latest)
            | Q(status="APROVADO", onboarding_aprovado_em__isnull=True, atualizado_em__lte=latest)
            | Q(status="PRECISA_CORRIGIR", criado_em__lte=latest)
        ).filter(
            Q(onboarding_lembrete_em__isnull=True)
            | Q(status="APROVADO", onboarding_aprovado_em__gt=start)
            | Q(status="PRECISA_CORRIGIR", criado_em__gt=start)
        ).values_list("pk", flat=True)

        sent = eligible = 0
        for pk in candidates.iterator():
            with transaction.atomic():
                pedido = PedidoEntrada.objects.select_for_update().get(pk=pk)
                anchor = (
                    pedido.onboarding_aprovado_em or pedido.atualizado_em
                    if pedido.status == "APROVADO" else pedido.criado_em
                )
                if anchor > latest or (anchor <= start and pedido.onboarding_lembrete_em):
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
                subject, message, path = step
                url = settings.NKATA_FRONTEND_URL.rstrip("/") + path
                greeting = f"Olá, {pedido.nome_completo.split()[0] if pedido.nome_completo.strip() else 'membro'}."
                if send_branded_email(
                    subject=subject, title=subject, recipient=pedido.email, greeting=greeting,
                    body=f"{greeting}\n\n{message}\n\nContinuar no NKATA: {url}",
                    paragraphs=[message], action_label="Continuar no NKATA", action_url=url,
                    notice="Faça a verificação apenas dentro do NKATA. Nunca envie a sua palavra-passe, BI ou selfie por email.",
                ):
                    PedidoEntrada.objects.filter(pk=pk).update(onboarding_lembrete_em=now)
                    sent += 1

        self.stdout.write(f"Lembretes elegíveis: {eligible}. Enviados: {sent}.")
