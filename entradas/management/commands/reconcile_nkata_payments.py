from django.core.management.base import BaseCommand
from entradas.models import PedidoPagamentoNKATA
from entradas.payment_service import PaymentError, reconcile


class Command(BaseCommand):
    help = "Consulta o prestador e reconcilia pagamentos abertos, sem criar cobranças."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        orders = PedidoPagamentoNKATA.objects.filter(
            estado__in=["PENDENTE", "INCERTO", "REVISAO", "FALHOU"],
            aplicado_em__isnull=True, provedor_id__isnull=False,
        ).order_by("ultima_verificacao", "criado_em")[:max(1, min(options["limit"], 50))]
        for order in orders:
            try:
                result = reconcile(order)
                self.stdout.write(f"{result.referencia}: {result.estado}")
            except PaymentError:
                self.stderr.write(f"{order.referencia}: consulta não concluída; tentar novamente.")
