import time

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from entradas.content_moderation_queue import (
    claim_next_analysis,
    process_claimed_analysis,
    queue_missing_pending_content,
    recover_stale_processing,
    requeue_failed_jobs,
)


class Command(BaseCommand):
    help = (
        "Processa em segundo plano a fila de pré-moderação NKATA. "
        "Use --watch para manter o worker ativo continuamente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Mantém o worker ativo aguardando novos trabalhos.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=2.0,
            help="Segundos entre consultas à fila quando --watch está ativo. Padrão: 2.",
        )
        parser.add_argument(
            "--batch",
            type=int,
            default=5,
            help="Máximo de itens processados por ciclo. Padrão: 5.",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Recoloca trabalhos com falha anterior na fila antes de iniciar.",
        )
        parser.add_argument(
            "--stale-minutes",
            type=int,
            default=15,
            help="Recupera trabalhos presos em processing há mais destes minutos. Padrão: 15.",
        )

    def _process_batch(self, limit):
        processed = 0
        failed = 0

        for _ in range(max(1, limit)):
            analysis = claim_next_analysis()
            if not analysis:
                break

            self.stdout.write(
                f"A processar {analysis.get_content_type_display()} #{analysis.content_id} "
                f"({analysis.media_type})..."
            )
            ok = process_claimed_analysis(analysis)
            processed += 1
            if ok:
                self.stdout.write(self.style.SUCCESS(
                    f"Concluído: {analysis.content_type} #{analysis.content_id}."
                ))
            else:
                failed += 1
                self.stdout.write(self.style.WARNING(
                    f"Falhou: {analysis.content_type} #{analysis.content_id}; "
                    "permanece Pendente para revisão humana."
                ))

        return processed, failed

    def handle(self, *args, **options):
        watch = bool(options.get("watch"))
        interval = max(0.5, float(options.get("interval") or 2.0))
        batch = max(1, int(options.get("batch") or 5))
        stale_minutes = max(1, int(options.get("stale_minutes") or 15))

        try:
            recovered = recover_stale_processing(minutes=stale_minutes)
            queued_missing = queue_missing_pending_content()
            retried = requeue_failed_jobs() if options.get("retry_failed") else 0
        except DatabaseError as exc:
            raise CommandError(
                "A fila de pré-moderação ainda não está pronta. Aplique primeiro "
                "`python manage.py migrate`."
            ) from exc

        if recovered:
            self.stdout.write(self.style.WARNING(
                f"{recovered} trabalho(s) interrompido(s) recuperado(s)."
            ))
        if queued_missing:
            self.stdout.write(
                f"{queued_missing} media pendente(s) antiga(s) adicionada(s) à fila."
            )
        if retried:
            self.stdout.write(
                f"{retried} trabalho(s) com falha recolocado(s) na fila."
            )

        self.stdout.write(self.style.SUCCESS(
            "Worker de pré-moderação NKATA iniciado"
            + (" em modo contínuo." if watch else " para um ciclo.")
        ))

        total_processed = 0
        total_failed = 0
        recovery_counter = 0

        try:
            while True:
                processed, failed = self._process_batch(batch)
                total_processed += processed
                total_failed += failed

                if not watch:
                    # Em modo único continua até esvaziar a fila, não apenas um batch.
                    if processed == 0:
                        break
                    continue

                if processed == 0:
                    time.sleep(interval)

                recovery_counter += 1
                if recovery_counter >= 30:
                    recover_stale_processing(minutes=stale_minutes)
                    recovery_counter = 0
        except KeyboardInterrupt:
            self.stdout.write("\nWorker interrompido pelo utilizador.")

        self.stdout.write(self.style.SUCCESS(
            f"Worker terminado: {total_processed} trabalho(s) processado(s), "
            f"{total_failed} com falha."
        ))
