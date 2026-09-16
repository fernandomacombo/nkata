from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from entradas.plan_service import (
    PLAN_DEFINITIONS,
    RECHARGE_PACKS,
    assign_plan,
    grant_recharge,
    recharge_balance_for_user,
)


User = get_user_model()


class Command(BaseCommand):
    help = (
        "Atribui um plano ou uma recarga para testes administrativos. "
        "Não substitui o futuro processamento de pagamentos."
    )

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("action", choices=["plan", "recharge"])
        parser.add_argument("value")

    def handle(self, *args, **options):
        email = str(options["email"]).strip()
        action = options["action"]
        value = str(options["value"]).strip().upper()

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError("Não existe uma conta NKATA com este email.")

        if action == "plan":
            if value not in PLAN_DEFINITIONS:
                raise CommandError("Use LIVRE, ESSENCIAL ou PREMIUM.")
            plan = assign_plan(user, value)
            self.stdout.write(self.style.SUCCESS(
                f"{email} agora está no {plan['label']}."
            ))
            return

        try:
            credits = int(value)
        except ValueError as exc:
            raise CommandError("A recarga deve ser 10, 30 ou 80.") from exc

        if credits not in RECHARGE_PACKS:
            raise CommandError("A recarga deve ser 10, 30 ou 80.")

        try:
            grant_recharge(user, credits)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        balance = recharge_balance_for_user(user)
        self.stdout.write(self.style.SUCCESS(
            f"Recarga de {credits} sinais adicionada a {email}. Saldo atual: {balance}."
        ))
