from datetime import timedelta

from django.db import DatabaseError, transaction
from django.utils import timezone

from .content_moderation_models import AnaliseAutomaticaConteudoNKATA
from .content_moderation_service import analyse_content_media
from .moments_models import MomentoNKATA
from .posts_models import PublicacaoNKATA


QUEUE_PROVIDER = "queue"
PROCESSING_PROVIDER = "processing"
FAILED_PROVIDER = "failed"
SKIPPED_PROVIDER = "skipped"


def queue_content_media_analysis(*, content_type, content_id, media_type):
    """Regista um trabalho leve sem analisar o ficheiro dentro do request HTTP."""
    content_type = str(content_type or "").strip().upper()
    media_type = str(media_type or "").strip().upper()
    if content_type not in {"MOMENTO", "PUBLICACAO"} or not content_id:
        return False
    if media_type not in {"IMAGEM", "VIDEO"}:
        return False

    defaults = {
        "media_type": media_type,
        "provider": QUEUE_PROVIDER,
        "model_name": "",
        "status": "REVISAO",
        "risk_level": "INDEFINIDO",
        "flagged": False,
        "categories": {},
        "category_scores": {},
        "notes": (
            "Aguardando processamento automático. O conteúdo permanece Pendente "
            "e invisível para outros membros até revisão humana."
        ),
    }

    try:
        AnaliseAutomaticaConteudoNKATA.objects.update_or_create(
            content_type=content_type,
            content_id=content_id,
            defaults=defaults,
        )
        return True
    except DatabaseError:
        # Fail closed: o conteúdo original continua PENDENTE. O comando de
        # backfill poderá enfileirá-lo depois que a tabela for preparada.
        return False


def recover_stale_processing(*, minutes=15):
    """Devolve à fila trabalhos abandonados por um worker interrompido."""
    threshold = timezone.now() - timedelta(minutes=max(1, int(minutes)))
    try:
        return AnaliseAutomaticaConteudoNKATA.objects.filter(
            provider=PROCESSING_PROVIDER,
            human_decision="",
            atualizado_em__lt=threshold,
        ).update(
            provider=QUEUE_PROVIDER,
            status="REVISAO",
            risk_level="INDEFINIDO",
            notes="Trabalho recuperado após interrupção do worker; aguardando nova tentativa.",
            atualizado_em=timezone.now(),
        )
    except DatabaseError:
        return 0


def requeue_failed_jobs():
    try:
        return AnaliseAutomaticaConteudoNKATA.objects.filter(
            provider=FAILED_PROVIDER,
            human_decision="",
        ).update(
            provider=QUEUE_PROVIDER,
            status="REVISAO",
            risk_level="INDEFINIDO",
            notes="Trabalho recolocado na fila para nova tentativa.",
            atualizado_em=timezone.now(),
        )
    except DatabaseError:
        return 0


def claim_next_analysis():
    """Reserva atomicamente um trabalho para evitar processamento duplicado."""
    try:
        candidate = (
            AnaliseAutomaticaConteudoNKATA.objects
            .filter(provider=QUEUE_PROVIDER, human_decision="")
            .order_by("criado_em", "id")
            .values_list("id", flat=True)
            .first()
        )
        if not candidate:
            return None

        with transaction.atomic():
            claimed = AnaliseAutomaticaConteudoNKATA.objects.filter(
                id=candidate,
                provider=QUEUE_PROVIDER,
                human_decision="",
            ).update(
                provider=PROCESSING_PROVIDER,
                notes="Pré-moderação automática em processamento.",
                atualizado_em=timezone.now(),
            )
        if not claimed:
            return None
        return AnaliseAutomaticaConteudoNKATA.objects.get(id=candidate)
    except DatabaseError:
        return None


def _pending_content_for(analysis):
    if analysis.content_type == "MOMENTO":
        return MomentoNKATA.objects.filter(
            id=analysis.content_id,
            moderacao_status="PENDENTE",
        ).first()
    if analysis.content_type == "PUBLICACAO":
        return PublicacaoNKATA.objects.filter(
            id=analysis.content_id,
            moderacao_status="PENDENTE",
        ).first()
    return None


def _mark_skipped(analysis, reason):
    try:
        AnaliseAutomaticaConteudoNKATA.objects.filter(id=analysis.id).update(
            provider=SKIPPED_PROVIDER,
            status="REVISAO",
            notes=str(reason)[:500],
            atualizado_em=timezone.now(),
        )
    except DatabaseError:
        pass


def _mark_failed(analysis, error):
    try:
        AnaliseAutomaticaConteudoNKATA.objects.filter(id=analysis.id).update(
            provider=FAILED_PROVIDER,
            status="ERRO",
            risk_level="INDEFINIDO",
            notes=(
                "Falha durante a pré-moderação assíncrona. O conteúdo continua "
                f"Pendente para revisão humana. Detalhe: {error}"
            )[:500],
            atualizado_em=timezone.now(),
        )
    except DatabaseError:
        pass


def process_claimed_analysis(analysis):
    """Executa um trabalho já reservado. Nunca aprova o conteúdo automaticamente."""
    if not analysis:
        return False

    try:
        content = _pending_content_for(analysis)
    except DatabaseError as exc:
        _mark_failed(analysis, exc)
        return False

    if not content:
        _mark_skipped(
            analysis,
            "Conteúdo já não está Pendente ou foi removido; análise automática ignorada.",
        )
        return True

    media = getattr(content, "media", None)
    if not media:
        _mark_skipped(analysis, "Conteúdo sem ficheiro de media; análise ignorada.")
        return True

    try:
        result = analyse_content_media(
            content_type=analysis.content_type,
            content_id=analysis.content_id,
            file_field=media,
            media_type=getattr(content, "tipo_media", analysis.media_type),
        )
    except Exception as exc:  # worker precisa permanecer vivo após falha de um item
        _mark_failed(analysis, exc)
        return False

    if result is None:
        _mark_failed(analysis, "não foi possível persistir o resultado automático")
        return False
    return True


def queue_missing_pending_content():
    """Enfileira media Pendente que ainda não possui registo de pré-moderação."""
    queued = 0

    for item in MomentoNKATA.objects.filter(
        moderacao_status="PENDENTE",
    ).exclude(media="").only("id", "tipo_media"):
        if not AnaliseAutomaticaConteudoNKATA.objects.filter(
            content_type="MOMENTO",
            content_id=item.id,
        ).exists():
            queued += int(queue_content_media_analysis(
                content_type="MOMENTO",
                content_id=item.id,
                media_type=item.tipo_media,
            ))

    for item in PublicacaoNKATA.objects.filter(
        moderacao_status="PENDENTE",
    ).exclude(media="").only("id", "tipo_media"):
        if not AnaliseAutomaticaConteudoNKATA.objects.filter(
            content_type="PUBLICACAO",
            content_id=item.id,
        ).exists():
            queued += int(queue_content_media_analysis(
                content_type="PUBLICACAO",
                content_id=item.id,
                media_type=item.tipo_media,
            ))

    return queued
