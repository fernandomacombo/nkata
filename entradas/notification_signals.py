import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AcaoPerfil, MatchPerfil, MensagemMatch
from .notification_models import NotificacaoNKATA


logger = logging.getLogger(__name__)

SIGNAL_NOTIFICATION_CONTENT = {
    "SINAL_FLOR": {
        "title": "Recebeu uma flor 🌹",
        "text": "{name} enviou-lhe uma flor.",
    },
    "SINAL_BEIJINHO": {
        "title": "Recebeu um beijinho 😘",
        "text": "{name} enviou-lhe um beijinho.",
    },
    "SINAL_OLA": {
        "title": "Um olá para si 👋",
        "text": "{name} disse olá e gostaria de conhecer melhor.",
    },
}


def _perfil_do_utilizador(user):
    if not user:
        return None
    return getattr(user, "perfil_nkata", None)


def _nome_publico(user):
    perfil = _perfil_do_utilizador(user)
    if perfil:
        return perfil.nome_publico
    return user.first_name or user.get_username()


def _executar_sem_bloquear_acao(callback):
    """Executa uma notificação como tarefa secundária.

    Uma falha no centro de notificações nunca pode anular um interesse,
    um sinal, um match ou uma mensagem que já foi guardada com sucesso.
    """
    try:
        callback()
    except Exception:  # noqa: BLE001 - fronteira deliberada de segurança
        logger.exception("Falha ao atualizar uma notificação do NKATA.")


def _depois_do_commit(callback):
    transaction.on_commit(
        lambda: _executar_sem_bloquear_acao(callback),
        robust=True,
    )


@receiver(post_save, sender=AcaoPerfil)
def notificar_novo_interesse(sender, instance, created, **kwargs):
    if not created or instance.tipo != "INTERESSE" or not instance.usuario_id:
        return

    destinatario = instance.perfil.usuario
    if not destinatario or destinatario.id == instance.usuario_id:
        return

    perfil_ator = _perfil_do_utilizador(instance.usuario)
    destinatario_id = destinatario.id
    ator_id = instance.usuario_id
    perfil_ator_id = perfil_ator.id if perfil_ator else None
    chave = f"interesse:{instance.pk}"
    nome = _nome_publico(instance.usuario)

    def criar():
        NotificacaoNKATA.objects.update_or_create(
            destinatario_id=destinatario_id,
            chave=chave,
            defaults={
                "ator_id": ator_id,
                "perfil_id": perfil_ator_id,
                "match": None,
                "tipo": "INTERESSE",
                "titulo": "Novo interesse",
                "texto": f"{nome} demonstrou interesse no seu perfil.",
                "lida": False,
            },
        )

    _depois_do_commit(criar)


@receiver(post_save, sender=AcaoPerfil)
def notificar_novo_sinal(sender, instance, created, **kwargs):
    content = SIGNAL_NOTIFICATION_CONTENT.get(instance.tipo)
    if not created or not content or not instance.usuario_id:
        return

    destinatario = instance.perfil.usuario
    if not destinatario or destinatario.id == instance.usuario_id:
        return

    perfil_ator = _perfil_do_utilizador(instance.usuario)
    destinatario_id = destinatario.id
    ator_id = instance.usuario_id
    perfil_ator_id = perfil_ator.id if perfil_ator else None
    nome = _nome_publico(instance.usuario)
    action_id = instance.pk

    def criar():
        NotificacaoNKATA.objects.update_or_create(
            destinatario_id=destinatario_id,
            chave=f"sinal:{action_id}",
            defaults={
                "ator_id": ator_id,
                "perfil_id": perfil_ator_id,
                "match": None,
                "tipo": "SINAL",
                "titulo": content["title"],
                "texto": content["text"].format(name=nome),
                "lida": False,
            },
        )

    _depois_do_commit(criar)


@receiver(post_delete, sender=AcaoPerfil)
def remover_notificacao_de_interesse(sender, instance, **kwargs):
    if instance.tipo != "INTERESSE":
        return

    chave = f"interesse:{instance.pk}"
    _depois_do_commit(
        lambda: NotificacaoNKATA.objects.filter(chave=chave).delete()
    )


@receiver(post_save, sender=MatchPerfil)
def notificar_match(sender, instance, created, update_fields=None, **kwargs):
    match_id = instance.id

    if instance.status != "ATIVO":
        _depois_do_commit(
            lambda: NotificacaoNKATA.objects.filter(match_id=match_id).update(lida=True)
        )
        return

    if not created and (not update_fields or "status" not in update_fields):
        return

    pares = [
        (instance.perfil_1, instance.perfil_2),
        (instance.perfil_2, instance.perfil_1),
    ]
    dados = [
        {
            "destinatario_id": perfil_destino.usuario_id,
            "ator_id": outro_perfil.usuario_id,
            "perfil_id": outro_perfil.id,
            "nome": outro_perfil.nome_publico,
        }
        for perfil_destino, outro_perfil in pares
        if perfil_destino.usuario_id
    ]

    def criar():
        for item in dados:
            # O aviso de match substitui o aviso simples de interesse dessa pessoa.
            NotificacaoNKATA.objects.filter(
                destinatario_id=item["destinatario_id"],
                perfil_id=item["perfil_id"],
                tipo="INTERESSE",
            ).delete()

            NotificacaoNKATA.objects.update_or_create(
                destinatario_id=item["destinatario_id"],
                chave=f"match:{match_id}",
                defaults={
                    "ator_id": item["ator_id"],
                    "perfil_id": item["perfil_id"],
                    "match_id": match_id,
                    "tipo": "MATCH",
                    "titulo": "É um match",
                    "texto": f"O interesse entre si e {item['nome']} é mútuo.",
                    "lida": False,
                },
            )

    _depois_do_commit(criar)


@receiver(post_save, sender=MensagemMatch)
def notificar_nova_mensagem(sender, instance, created, **kwargs):
    if not created or not instance.remetente_id or instance.match.status != "ATIVO":
        return

    perfil_remetente = _perfil_do_utilizador(instance.remetente)
    if not perfil_remetente:
        return

    if instance.match.perfil_1_id == perfil_remetente.id:
        perfil_destino = instance.match.perfil_2
    elif instance.match.perfil_2_id == perfil_remetente.id:
        perfil_destino = instance.match.perfil_1
    else:
        return

    if not perfil_destino.usuario_id:
        return

    resumo = " ".join(instance.texto.split())
    if len(resumo) > 95:
        resumo = f"{resumo[:92].rstrip()}…"

    destinatario_id = perfil_destino.usuario_id
    remetente_id = instance.remetente_id
    perfil_remetente_id = perfil_remetente.id
    perfil_remetente_nome = perfil_remetente.nome_publico
    match_id = instance.match_id

    def criar():
        NotificacaoNKATA.objects.update_or_create(
            destinatario_id=destinatario_id,
            chave=f"mensagem:{match_id}",
            defaults={
                "ator_id": remetente_id,
                "perfil_id": perfil_remetente_id,
                "match_id": match_id,
                "tipo": "MENSAGEM",
                "titulo": f"Mensagem de {perfil_remetente_nome}",
                "texto": resumo,
                "lida": False,
            },
        )

    _depois_do_commit(criar)
