import logging

from django.db import DatabaseError

from .notification_models import NotificacaoNKATA
from .posts_models import ReacaoPublicacaoNKATA


logger = logging.getLogger(__name__)

REACTION_OPTIONS = [
    {"value": "GOSTEI", "label": "Gostei", "icon": "heart"},
    {"value": "FLOR", "label": "Flor", "icon": "flower"},
    {"value": "APRECIAR", "label": "Apreciar", "icon": "sparkles"},
]
REACTION_BY_CODE = {item["value"]: item for item in REACTION_OPTIONS}


def reaction_payload(user, publicacao):
    counts = {item["value"]: 0 for item in REACTION_OPTIONS}
    mine = None

    try:
        rows = ReacaoPublicacaoNKATA.objects.filter(
            publicacao=publicacao,
        ).values_list("usuario_id", "tipo")
        for user_id, reaction_type in rows:
            if reaction_type in counts:
                counts[reaction_type] += 1
            if user and user.is_authenticated and user_id == user.id:
                mine = reaction_type
    except DatabaseError:
        return {
            "enabled": False,
            "setup_required": True,
            "mine": None,
            "total": 0,
            "counts": counts,
            "options": REACTION_OPTIONS,
        }

    return {
        "enabled": publicacao.usuario_id != getattr(user, "id", None),
        "setup_required": False,
        "mine": mine,
        "total": sum(counts.values()),
        "counts": counts,
        "options": REACTION_OPTIONS,
    }


def _notification_key(publicacao_id, user_id):
    return f"publicacao-reacao:{publicacao_id}:{user_id}"


def _remove_notification(publicacao, user):
    try:
        NotificacaoNKATA.objects.filter(
            destinatario_id=publicacao.usuario_id,
            chave=_notification_key(publicacao.id, user.id),
        ).delete()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao remover notificação de reação em publicação.")


def _update_notification(publicacao, user, actor_profile, reaction_type):
    option = REACTION_BY_CODE[reaction_type]
    actor_name = actor_profile.nome_publico

    try:
        NotificacaoNKATA.objects.update_or_create(
            destinatario_id=publicacao.usuario_id,
            chave=_notification_key(publicacao.id, user.id),
            defaults={
                "ator_id": user.id,
                "perfil_id": actor_profile.id,
                "match": None,
                "tipo": "PUBLICACAO",
                "titulo": "Reação na sua publicação",
                "texto": f"{actor_name} reagiu com {option['label'].lower()} à sua publicação.",
                "lida": False,
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao criar notificação de reação em publicação.")


def toggle_reaction(user, actor_profile, publicacao, reaction_type):
    if reaction_type not in REACTION_BY_CODE:
        raise ValueError("invalid_reaction")

    current = ReacaoPublicacaoNKATA.objects.filter(
        publicacao=publicacao,
        usuario=user,
    ).first()

    if current and current.tipo == reaction_type:
        current.delete()
        _remove_notification(publicacao, user)
        return False, None

    if current:
        current.tipo = reaction_type
        current.save(update_fields=["tipo", "atualizado_em"])
    else:
        ReacaoPublicacaoNKATA.objects.create(
            publicacao=publicacao,
            usuario=user,
            tipo=reaction_type,
        )

    _update_notification(publicacao, user, actor_profile, reaction_type)
    return True, reaction_type
