from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ...branded_email import send_branded_email
from ...identity_models import pedido_tem_identidade_verificada
from ...models import PerfilNKATA


class Command(BaseCommand):
    help = "Conta ou envia um único convite de regresso a membros verificados e inativos."

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Enviar emails. Por defeito, conta apenas.")

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(days=7)
        candidates = PerfilNKATA.objects.filter(
            status="ATIVO",
            visivel=True,
            encerramento_solicitado_em__isnull=True,
            pedido__status="APROVADO",
            pedido__questionario__isnull=False,
            usuario__is_active=True,
            usuario__is_staff=False,
            usuario__is_superuser=False,
            reativacao_enviada_em__isnull=True,
        ).exclude(usuario__email="").filter(
            Q(usuario__last_login__lte=cutoff)
            | Q(usuario__last_login__isnull=True, criado_em__lte=cutoff, usuario__date_joined__lte=cutoff)
        )

        eligible = sent = 0
        for pk in candidates.values_list("pk", flat=True).iterator():
            with transaction.atomic():
                profile = candidates.select_related("usuario", "pedido").select_for_update(
                    of=("self",)
                ).filter(pk=pk).first()
                if not profile or not profile.usuario.has_usable_password():
                    continue
                if not pedido_tem_identidade_verificada(profile.pedido):
                    continue
                eligible += 1
                if not options["send"]:
                    continue

                subject = "Volte a explorar o NKATA"
                greeting = "Olá!"
                message = "A sua conta está pronta. Quando quiser voltar, entre no NKATA para explorar perfis e conhecer pessoas com intenções semelhantes às suas."
                url = f"{settings.NKATA_FRONTEND_URL.rstrip('/')}/entrar/"
                if send_branded_email(
                    subject=subject, title=subject, recipient=profile.usuario.email,
                    greeting=greeting, paragraphs=[message],
                    body=f"{greeting}\n\n{message}\n\n{url}",
                    action_label="Entrar no NKATA", action_url=url,
                    notice="Este convite de regresso é enviado uma única vez.",
                ):
                    profile.reativacao_enviada_em = timezone.now()
                    profile.save(update_fields=["reativacao_enviada_em"])
                    sent += 1

        self.stdout.write(f"Contas elegíveis: {eligible}. Emails enviados: {sent}.")
