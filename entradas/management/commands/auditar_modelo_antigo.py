from django.core.management.base import BaseCommand
from entradas.legacy_commercial import legacy_audit


class Command(BaseCommand):
    help = "Contagem de pagamentos e benefícios antigos, sem alterar dados."

    def handle(self, *args, **options):
        for name, count in legacy_audit().items():
            self.stdout.write(f"{name}: {count}")
