from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AcaoPerfil, MatchPerfil, MensagemMatch
from .notification_models import NotificacaoNKATA


def _perfil_do_utilizador(user):
    if not user:
        return None
    return getattr(user, "perfil_nkata", None)


def _nome_publico(user):
    perfil = _perfil_do_utilizador(user)
    if perfil:
        return perfil.nome_publico
    return user.first_name or user.get_username()


@receiver(post_save, sender=AcaoPerfil)
def notificar_novo_interesse(sender, instance, created, **kwargs):
    if not created or instance.tipo != "INTERESSE" or not instance.usuario_id:
        return

    destinatario = instance.perfil.usuario
    if not destinatario or destinatario.id == instance.usuario_id:
        return

    perfil_ator = _perfil_do_utilizador(instance.usuario)
    NotificacaoNKATA.objects.update_or_create(
        destinatario=destinatario,
        chave=f"interesse:{instance.pk}",
        defaults={
            "ator": instance.usuario,
            "perfil": perfil_ator,
            "match": None,
            "tipo": "INTERESSE",
            "titulo": "Novo interesse",
            "texto": f"{_nome_publico(instance.usuario)} demonstrou interesse no seu perfil.",
            "lida": False,
        },
    )


@receiver(post_delete, sender=AcaoPerfil)
def remover_notificacao_de_interesse(sender, instance, **kwargs):
    if instance.tipo == "INTERESSE":
        NotificacaoNKATA.objects.filter(chave=f"interesse:{instance.pk}").delete()


@receiver(post_save, sender=MatchPerfil)
def notificar_match(sender, instance, **kwargs):
    if instance.status != "ATIVO":
        NotificacaoNKATA.objects.filter(match=instance).update(lida=True)
        return

    pares = [
        (instance.perfil_1, instance.perfil_2),
        (instance.perfil_2, instance.perfil_1),
    ]

    for perfil_destino, outro_perfil in pares:
        if not perfil_destino.usuario_id:
            continue

        NotificacaoNKATA.objects.update_or_create(
            destinatario=perfil_destino.usuario,
            chave=f"match:{instance.pk}",
            defaults={
                "ator": outro_perfil.usuario,
                "perfil": outro_perfil,
                "match": instance,
                "tipo": "MATCH",
                "titulo": "É um match",
                "texto": f"O interesse entre si e {outro_perfil.nome_publico} é mútuo.",
                "lida": False,
            },
        )


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

    NotificacaoNKATA.objects.update_or_create(
        destinatario=perfil_destino.usuario,
        chave=f"mensagem:{instance.match_id}",
        defaults={
            "ator": instance.remetente,
            "perfil": perfil_remetente,
            "match": instance.match,
            "tipo": "MENSAGEM",
            "titulo": f"Mensagem de {perfil_remetente.nome_publico}",
            "texto": resumo,
            "lida": False,
        },
    )
