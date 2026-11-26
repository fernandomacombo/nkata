"""Read-only audit of financial invariants, no provider calls, no balance repairs."""
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Q
from entradas.credit_catalog import WELCOME_CREDITS
from entradas.models import CarteiraNKATA, MovimentoCreditoNKATA, PedidoPagamentoNKATA, BonusIdentidadeCreditoNKATA, EnvioMomentoCreditoNKATA
from entradas.moments_models import MomentoNKATA


class Command(BaseCommand):
    help = "Audita a cadeia de créditos, recargas Paysuit e bónus. Não altera dados."

    def handle(self, *args, **options):
        issues = 0
        wallets = orders = movements = bonuses = moment_receipts = 0
        def flag(kind, pk):
            nonlocal issues
            issues += 1
            # Internal numeric IDs / order UUID only; no email, BI, tokens or documents.
            if issues <= 100:
                self.stderr.write(f"{kind}: {pk}")
        with transaction.atomic():
            if connection.vendor == "postgresql":
                # Consistent snapshot across all tables, without blocking payments.
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            for wallet in CarteiraNKATA.objects.all().iterator(chunk_size=200):
                wallets += 1
                running = 0
                for move in wallet.movimentos.order_by("pk").iterator(chunk_size=500):
                    movements += 1
                    running += move.quantidade
                    if running < 0 or move.saldo_apos != running:
                        flag("CADEIA_MOVIMENTO", move.pk)
                if running != wallet.saldo:
                    flag("SALDO_DIVERGENTE", wallet.pk)
            for order in PedidoPagamentoNKATA.objects.filter(produto__startswith="CREDITOS_").iterator(chunk_size=200):
                orders += 1
                move = MovimentoCreditoNKATA.objects.filter(carteira__usuario_id=order.usuario_id, chave=f"{'simulated' if order.simulado else 'paysuite'}:{order.pk}").first()
                paid = order.estado == "PAGO" and bool(order.confirmado_em and order.aplicado_em)
                if paid:
                    if not move or (move.tipo, move.quantidade, move.referencia) != ("RECARGA", order.creditos, order.referencia):
                        flag("RECARGA_SEM_LIQUIDACAO_CORRETA", order.pk)
                elif move or order.estado == "PAGO" or order.aplicado_em:
                    flag("LIQUIDACAO_INCONSISTENTE", order.pk)
                elif order.confirmado_em:
                    flag("PAGAMENTO_CONFIRMADO_EM_REVISAO", order.pk)
            for move in MovimentoCreditoNKATA.objects.filter(Q(chave__startswith="paysuite:") | Q(chave__startswith="simulated:")).iterator(chunk_size=200):
                prefix, order_id = move.chave.split(":", 1)
                try:
                    exists = PedidoPagamentoNKATA.objects.filter(pk=order_id, usuario_id=move.carteira.usuario_id,
                        produto__startswith="CREDITOS_", simulado=(prefix=="simulated")).exists()
                except (ValueError, TypeError):
                    exists = False
                except Exception as error:
                    from django.core.exceptions import ValidationError
                    if not isinstance(error, ValidationError):
                        raise
                    exists = False
                if not exists:
                    flag("RECARGA_SEM_PEDIDO", move.pk)
            for award in BonusIdentidadeCreditoNKATA.objects.select_related("movimento").iterator(chunk_size=200):
                bonuses += 1
                if award.movimento.tipo != "BONUS" or award.movimento.chave != "welcome:v1" or award.movimento.quantidade != WELCOME_CREDITS:
                    flag("BONUS_INCONSISTENTE", award.pk)
            for move in MovimentoCreditoNKATA.objects.filter(chave="welcome:v1", bonus_identidade__isnull=True):
                flag("BONUS_SEM_IDENTIDADE", move.pk)
            for receipt in EnvioMomentoCreditoNKATA.objects.select_related("movimento__carteira").iterator(chunk_size=200):
                moment_receipts += 1
                move = receipt.movimento
                key = str(receipt.chave)
                reference = f"MOMENTO:{key}"
                if receipt.custo and (not move or (move.carteira.usuario_id, move.chave, move.tipo, move.quantidade, move.referencia) != (receipt.usuario_id, f"moment:{key}", "CONSUMO", -receipt.custo, reference)):
                    flag("MOMENTO_DEBITO_INCONSISTENTE", receipt.pk)
                if not receipt.custo and move:
                    flag("MOMENTO_GRATUITO_COM_DEBITO", receipt.pk)
                refund = MovimentoCreditoNKATA.objects.filter(carteira__usuario_id=receipt.usuario_id, chave=f"moment-refund:{key}").first()
                moment = MomentoNKATA.objects.filter(pk=receipt.momento_id).first()
                if moment and (moment.usuario_id != receipt.usuario_id or moment.tipo_media != receipt.tipo_media):
                    flag("MOMENTO_RECIBO_INCONSISTENTE", receipt.pk)
                if refund and (not receipt.custo or (refund.tipo, refund.quantidade, refund.referencia) != ("ESTORNO", receipt.custo, reference)):
                    flag("MOMENTO_ESTORNO_INCONSISTENTE", receipt.pk)
                if moment and ((moment.moderacao_status == "REJEITADO" and receipt.custo and not refund) or (moment.moderacao_status != "REJEITADO" and refund)):
                    flag("MOMENTO_ESTORNO_MODERACAO", receipt.pk)
            for move in MovimentoCreditoNKATA.objects.filter(Q(chave__startswith="moment:") | Q(chave__startswith="moment-refund:")).iterator(chunk_size=200):
                prefix, raw_key = move.chave.split(":", 1)
                try:
                    key = uuid.UUID(raw_key)
                except ValueError:
                    flag("MOMENTO_CHAVE_INVALIDA", move.pk)
                    continue
                receipt = EnvioMomentoCreditoNKATA.objects.filter(usuario_id=move.carteira.usuario_id, chave=key).first()
                if not receipt or (prefix == "moment" and receipt.movimento_id != move.pk):
                    flag("MOMENTO_MOVIMENTO_SEM_RECIBO", move.pk)
        self.stdout.write(f"Carteiras: {wallets}; movimentos: {movements}; pedidos: {orders}; bónus: {bonuses}; recibos de Momentos: {moment_receipts}; ocorrências: {issues}.")
        if issues:
            raise CommandError("Auditoria financeira encontrou ocorrências. Não foram alterados dados.")
