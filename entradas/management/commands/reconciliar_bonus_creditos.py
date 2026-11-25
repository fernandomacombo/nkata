from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from entradas.models import PerfilNKATA, MovimentoCreditoNKATA, BonusIdentidadeCreditoNKATA, AcessoPlanoNKATA
from entradas.wallet_service import welcome_eligible, grant_welcome_credits, WalletError
from entradas.legacy_commercial import convertible_quinzenal


class Command(BaseCommand):
    help = "Pré-visualiza ou atribui uma única vez o bónus de identidade. Sem alterações por omissão."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        apply = options["apply"]
        if apply and not settings.NKATA_CREDIT_TRANSITION_ENABLED:
            raise CommandError("A transição de créditos está desativada.")
        eligible = existing = granted = review = 0
        profiles = PerfilNKATA.objects.filter(status="ATIVO", usuario__isnull=False,
            pedido__documento_confirmado=True, pedido__verificacao_identidade__status="APROVADA"
        ).select_related("usuario", "pedido", "pedido__verificacao_identidade")
        for profile in profiles.iterator(chunk_size=200):
            if not welcome_eligible(profile):
                continue
            granted_before = MovimentoCreditoNKATA.objects.filter(carteira__usuario_id=profile.usuario_id, chave="welcome:v1").exists()
            promotional = convertible_quinzenal(profile.usuario_id).exists()
            if granted_before and not promotional:
                existing += 1
                continue
            if not granted_before and BonusIdentidadeCreditoNKATA.objects.filter(documento_chave=profile.pedido.documento_chave).exists():
                review += 1
                continue
            eligible += 1
            if apply:
                try:
                    grant_welcome_credits(profile.usuario)
                    granted += 1
                except WalletError:
                    review += 1
        self.stdout.write(f"Modo: {'aplicar' if apply else 'simulação'}; elegíveis: {eligible}; já atribuídos: {existing}; processados: {granted}; revisão: {review}.")
