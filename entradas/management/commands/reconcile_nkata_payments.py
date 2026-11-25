import time
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import F, Q
from django.utils import timezone
from entradas.models import PedidoPagamentoNKATA
from entradas.payment_service import PaymentError, reconcile, simulation_enabled

# One batch per database, including overlapping deployments.
RECONCILIATION_LOCK = 72601931


class Command(BaseCommand):
    help = "Consulta o prestador e reconcilia pagamentos abertos, sem criar cobranças."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=60)

    def handle(self, *args, **options):
        if simulation_enabled():
            raise CommandError("Reconciliação real indisponível em simulação.")
        if not settings.NKATA_PAYSUITE_TOKEN:
            raise CommandError("Configure as credenciais do prestador antes de reconciliar pagamentos.")
        while True:
            self.reconcile_batch(options["limit"])
            if not options["watch"]:
                return
            time.sleep(max(30, min(options["interval"], 3600)))

    def reconcile_batch(self, limit):
        locked = False
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", [RECONCILIATION_LOCK])
                locked = cursor.fetchone()[0]
            if not locked:
                return
        try:
            self._process_due_orders(limit)
        finally:
            if locked:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(%s)", [RECONCILIATION_LOCK])

    def _process_due_orders(self, limit):
        now = timezone.now()
        # New checkouts need quick confirmation; older unresolved orders can
        # be checked less often. Keep checking indefinitely: a late payment
        # must still be honoured, even after a failure reported by the provider.
        open_states = ["CRIADO", "PENDENTE", "INCERTO"]
        due = (
            Q(estado__in=open_states, criado_em__gt=now-timedelta(minutes=15),
              ultima_verificacao__lte=now-timedelta(seconds=60))
            | Q(estado__in=open_states, criado_em__lte=now-timedelta(minutes=15),
                criado_em__gt=now-timedelta(hours=2),
                ultima_verificacao__lte=now-timedelta(minutes=5))
            | Q(estado__in=open_states, criado_em__lte=now-timedelta(hours=2),
                criado_em__gt=now-timedelta(days=1),
                ultima_verificacao__lte=now-timedelta(minutes=30))
            | Q(estado__in=open_states, criado_em__lte=now-timedelta(days=1),
                ultima_verificacao__lte=now-timedelta(hours=6))
            | Q(estado="REVISAO", ultima_verificacao__lte=now-timedelta(minutes=15))
            | Q(estado="FALHOU", criado_em__gt=now-timedelta(days=1),
                ultima_verificacao__lte=now-timedelta(hours=1))
            | Q(estado="FALHOU", criado_em__lte=now-timedelta(days=1),
                ultima_verificacao__lte=now-timedelta(days=1))
            | Q(estado__in=open_states + ["REVISAO", "FALHOU"],
                ultima_verificacao__isnull=True)
        )
        orders = list(PedidoPagamentoNKATA.objects.filter(
            due, simulado=False, aplicado_em__isnull=True, provedor_id__isnull=False,
        ).exclude(provedor_id="").order_by(
            F("ultima_verificacao").asc(nulls_first=True), "criado_em", "pk"
        )[:max(1, min(limit, 50))])
        for order in orders:
            try:
                result = reconcile(order)
                self.stdout.write(f"{result.referencia}: {result.estado}")
            except PaymentError:
                # Record the attempt only, not a provider confirmation. Rotate
                # failing orders so they cannot starve newer payments.
                PedidoPagamentoNKATA.objects.filter(
                    pk=order.pk, aplicado_em__isnull=True
                ).update(ultima_verificacao=timezone.now())
                self.stderr.write(f"{order.referencia}: consulta não concluída; tentar novamente.")
