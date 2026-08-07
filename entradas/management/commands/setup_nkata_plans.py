from django.core.management.base import BaseCommand

from entradas.plan_service import (
    PLAN_GROUP_ESSENCIAL,
    PLAN_GROUP_PREMIUM,
    ensure_plan_groups,
)


class Command(BaseCommand):
    help = "Cria os grupos nativos usados pelos planos pagos do NKATA."

    def handle(self, *args, **options):
        ensure_plan_groups()
        self.stdout.write(self.style.SUCCESS(
            "Planos preparados: "
            f"{PLAN_GROUP_ESSENCIAL} e {PLAN_GROUP_PREMIUM}. "
            "O plano Livre não precisa de grupo."
        ))
