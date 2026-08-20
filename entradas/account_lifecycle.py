from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .identity_models import pedido_tem_identidade_verificada
from .models import PedidoEntrada, PerfilNKATA


User = get_user_model()


def pedido_tem_questionario(pedido):
    try:
        pedido.questionario
    except ObjectDoesNotExist:
        return False
    return True


def perfil_pronto_para_publicar(perfil):
    if not perfil.usuario_id:
        return False

    if not perfil.usuario.has_usable_password():
        return False

    if perfil.pedido.status != "APROVADO":
        return False

    if not pedido_tem_identidade_verificada(perfil.pedido):
        return False

    return pedido_tem_questionario(perfil.pedido)


@receiver(pre_save, sender=PerfilNKATA)
def manter_perfil_privado_ate_conta_ficar_pronta(sender, instance, **kwargs):
    """
    Um perfil nunca deve ficar público antes de o pedido estar aprovado,
    o questionário estar concluído e o titular ter criado a própria senha.
    """
    if instance.status == "BLOQUEADO":
        instance.visivel = False
        return

    if not perfil_pronto_para_publicar(instance):
        instance.status = "PAUSADO"
        instance.visivel = False


@receiver(pre_save, sender=User)
def detetar_primeira_palavra_passe_utilizavel(sender, instance, **kwargs):
    """Regista apenas a transição inicial de senha inutilizável para utilizável."""
    if not instance.pk:
        instance._nkata_password_became_usable = instance.has_usable_password()
        return

    try:
        anterior = sender.objects.only("password").get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._nkata_password_became_usable = instance.has_usable_password()
        return

    instance._nkata_password_became_usable = (
        not anterior.has_usable_password() and instance.has_usable_password()
    )


@receiver(post_save, sender=User)
def ativar_perfil_depois_da_criacao_da_senha(sender, instance, **kwargs):
    """Ativa o perfil somente quando o titular cria a primeira senha válida."""
    if not getattr(instance, "_nkata_password_became_usable", False):
        return

    perfil = (
        PerfilNKATA.objects
        .select_related("pedido", "usuario")
        .filter(usuario=instance)
        .first()
    )

    if not perfil or perfil.status == "BLOQUEADO":
        return

    if not perfil_pronto_para_publicar(perfil):
        return

    PerfilNKATA.objects.filter(pk=perfil.pk).update(
        status="ATIVO",
        visivel=True,
    )


@receiver(post_save, sender=PedidoEntrada)
def ocultar_perfil_quando_pedido_deixa_de_estar_aprovado(sender, instance, **kwargs):
    """Recusa, bloqueio ou nova análise retiram imediatamente o perfil do público."""
    if instance.status == "APROVADO":
        return

    perfil = PerfilNKATA.objects.filter(pedido=instance).first()
    if not perfil:
        return

    novo_status = "BLOQUEADO" if instance.status == "BLOQUEADO" else "PAUSADO"
    PerfilNKATA.objects.filter(pk=perfil.pk).update(
        status=novo_status,
        visivel=False,
    )
