from django.core.management.base import BaseCommand

from entradas.content_moderation_service import analyse_content_media, analysis_for
from entradas.moments_models import MomentoNKATA
from entradas.posts_models import PublicacaoNKATA


class Command(BaseCommand):
    help = (
        "Executa a pré-moderação de media pendente em Momentos e Publicações. "
        "Por padrão ignora conteúdos que já tenham análise registrada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Executa novamente mesmo quando já existe uma análise.",
        )

    def _analyse_queryset(self, queryset, content_type, force=False):
        analysed = 0
        skipped = 0

        for item in queryset.iterator():
            if not item.media:
                continue
            if not force and analysis_for(content_type, item.pk):
                skipped += 1
                continue

            analysis = analyse_content_media(
                content_type=content_type,
                content_id=item.pk,
                file_field=item.media,
                media_type=item.tipo_media,
            )
            if analysis:
                analysed += 1

        return analysed, skipped

    def handle(self, *args, **options):
        force = bool(options.get("force"))

        moments = MomentoNKATA.objects.filter(
            moderacao_status="PENDENTE",
        ).exclude(media="")
        posts = PublicacaoNKATA.objects.filter(
            moderacao_status="PENDENTE",
        ).exclude(media="")

        moments_analysed, moments_skipped = self._analyse_queryset(
            moments,
            "MOMENTO",
            force=force,
        )
        posts_analysed, posts_skipped = self._analyse_queryset(
            posts,
            "PUBLICACAO",
            force=force,
        )

        self.stdout.write(self.style.SUCCESS(
            "Pré-moderação concluída: "
            f"{moments_analysed} Momento(s) analisado(s), "
            f"{posts_analysed} Publicação/Publicações analisada(s)."
        ))
        if moments_skipped or posts_skipped:
            self.stdout.write(
                f"Ignorados por já terem análise: {moments_skipped} Momento(s), "
                f"{posts_skipped} Publicação/Publicações. Use --force para repetir."
            )
