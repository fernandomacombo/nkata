import logging

from django.db import DatabaseError

from .notification_models import NotificacaoNKATA
from .moments_models import ReacaoMomentoNKATA


logger = logging.getLogger(__name__)

REACTION_OPTIONS = [
    {"value": "CORACAO", "label": "Gostei", "icon": "heart"},
    {"value": "FLOR", "label": "Flor", "icon": "flower"},
    {"value": "APLAUSO", "label": "Bonito", "icon": "sparkles"},
]
REACTION_BY_CODE = {item["value"]: item for item in REACTION_OPTIONS}


def reaction_payload(user, momento):
    counts = {item["value"]: 0 for item in REACTION_OPTIONS}
    mine = None

    try:
        rows = ReacaoMomentoNKATA.objects.filter(
            momento=momento,
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
        "enabled": momento.usuario_id != getattr(user, "id", None),
        "setup_required": False,
        "mine": mine,
        "total": sum(counts.values()),
        "counts": counts,
        "options": REACTION_OPTIONS,
    }


def _notification_key(momento_id, user_id):
    return f"momento-reacao:{momento_id}:{user_id}"


def _remove_notification(momento, user):
    try:
        NotificacaoNKATA.objects.filter(
            destinatario_id=momento.usuario_id,
            chave=_notification_key(momento.id, user.id),
        ).delete()
    except Exception:  # noqa: BLE001 - notificação não bloqueia a reação
        logger.exception("Falha ao remover notificação de reação em Momento.")


def _update_notification(momento, user, actor_profile, reaction_type):
    option = REACTION_BY_CODE[reaction_type]
    actor_name = actor_profile.nome_publico

    try:
        NotificacaoNKATA.objects.update_or_create(
            destinatario_id=momento.usuario_id,
            chave=_notification_key(momento.id, user.id),
            defaults={
                "ator_id": user.id,
                "perfil_id": actor_profile.id,
                "match": None,
                "tipo": "MOMENTO",
                "titulo": "Reação no seu Momento",
                "texto": f"{actor_name} reagiu com {option['label'].lower()} ao seu Momento.",
                "lida": False,
            },
        )
    except Exception:  # noqa: BLE001 - notificação não bloqueia a reação
        logger.exception("Falha ao criar notificação de reação em Momento.")


def toggle_reaction(user, actor_profile, momento, reaction_type):
    if reaction_type not in REACTION_BY_CODE:
        raise ValueError("invalid_reaction")

    current = ReacaoMomentoNKATA.objects.filter(
        momento=momento,
        usuario=user,
    ).first()

    if current and current.tipo == reaction_type:
        current.delete()
        _remove_notification(momento, user)
        return False, None

    if current:
        current.tipo = reaction_type
        current.save(update_fields=["tipo", "atualizado_em"])
    else:
        ReacaoMomentoNKATA.objects.create(
            momento=momento,
            usuario=user,
            tipo=reaction_type,
        )

    _update_notification(momento, user, actor_profile, reaction_type)
    return True, reaction_type
