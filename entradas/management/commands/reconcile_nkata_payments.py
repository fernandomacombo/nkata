import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from entradas.models import PedidoPagamentoNKATA
from entradas.payment_service import PaymentError, reconcile


class Command(BaseCommand):
    help = "Consulta o prestador e reconcilia pagamentos abertos, sem criar cobranças."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=60)

    def handle(self, *args, **options):
        if options["watch"] and not settings.NKATA_PAYSUITE_TOKEN:
            raise CommandError("Configure as credenciais do prestador antes de iniciar a reconciliação contínua.")
        while True:
            self.reconcile_batch(options["limit"])
            if not options["watch"]:
                return
            time.sleep(max(30, min(options["interval"], 3600)))

    def reconcile_batch(self, limit):
        orders = PedidoPagamentoNKATA.objects.filter(
            estado__in=["PENDENTE", "INCERTO", "REVISAO", "FALHOU"],
            aplicado_em__isnull=True, provedor_id__isnull=False,
        ).order_by("ultima_verificacao", "criado_em")[:max(1, min(limit, 50))]
        for order in orders:
            try:
                result = reconcile(order)
                self.stdout.write(f"{result.referencia}: {result.estado}")
            except PaymentError:
                self.stderr.write(f"{order.referencia}: consulta não concluída; tentar novamente.")
