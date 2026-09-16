from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import PedidoEntrada


NOTIFIABLE_STATUSES = {
    "APROVADO",
    "PRECISA_CORRIGIR",
    "RECUSADO",
    "BLOQUEADO",
}


def _primeiro_nome(nome_completo):
    partes = str(nome_completo or "").strip().split()
    return partes[0] if partes else "Olá"


def build_access_status_email(pedido):
    """Constrói o assunto e o corpo sem expor notas internas do Admin."""
    primeiro_nome = _primeiro_nome(pedido.nome_completo)
    frontend = settings.NKATA_FRONTEND_URL.rstrip("/")
    acompanhamento_url = f"{frontend}/acompanhar-pedido/"

    if pedido.status == "APROVADO":
        questionario_url = f"{frontend}/questionario/{pedido.token}/"
        subject = "O seu pedido NKATA foi aprovado"
        body = (
            f"Olá {primeiro_nome},\n\n"
            "O seu pedido de entrada no NKATA foi aprovado.\n\n"
            "O próximo passo é responder ao questionário e criar a sua própria palavra-passe. "
            "O seu perfil só ficará ativo depois de concluir estas etapas.\n\n"
            f"Continuar no NKATA:\n{questionario_url}\n\n"
            "Este link é pessoal. Não o partilhe com outras pessoas.\n\n"
            f"Também pode acompanhar o pedido em:\n{acompanhamento_url}\n\n"
            "NKATA\nRelações sérias começam com intenções claras."
        )
        return subject, body

    if pedido.status == "PRECISA_CORRIGIR":
        verification = getattr(pedido, "verificacao_identidade", None)
        recapture_url = ""
        if verification and verification.status == "REPETIR":
            recapture_url = (
                f"\n\nRepetir a verificação pela câmara:\n"
                f"{frontend}/verificar-identidade/{verification.token}/"
            )
        subject = "Precisamos rever alguns dados do seu pedido NKATA"
        body = (
            f"Olá {primeiro_nome},\n\n"
            "A análise do seu pedido identificou informação que precisa de ser revista antes de continuarmos.\n\n"
            "Por segurança, notas internas da análise não são enviadas automaticamente por email."
            f"{recapture_url}\n\n"
            f"Acompanhar o pedido:\n{acompanhamento_url}\n\n"
            "NKATA"
        )
        return subject, body

    if pedido.status == "RECUSADO":
        subject = "Atualização sobre o seu pedido NKATA"
        body = (
            f"Olá {primeiro_nome},\n\n"
            "A análise do seu pedido foi concluída e, neste momento, a entrada não foi aprovada.\n\n"
            f"Pode consultar o estado do pedido em:\n{acompanhamento_url}\n\n"
            "Obrigado pelo interesse no NKATA."
        )
        return subject, body

    if pedido.status == "BLOQUEADO":
        subject = "Atualização sobre o seu pedido NKATA"
        body = (
            f"Olá {primeiro_nome},\n\n"
            "O seu pedido encontra-se indisponível e não pode continuar neste momento.\n\n"
            "Se precisar de esclarecer a situação, utilize apenas os canais oficiais do NKATA.\n\n"
            f"Consultar o estado do pedido:\n{acompanhamento_url}\n\n"
            "NKATA"
        )
        return subject, body

    return None, None


def build_access_receipt_email(pedido):
    """Constrói o recibo privado usado no envio inicial e na recuperação."""
    primeiro_nome = _primeiro_nome(pedido.nome_completo)
    frontend = settings.NKATA_FRONTEND_URL.rstrip("/")
    acompanhamento_url = f"{frontend}/acompanhar-pedido/"
    subject = "Código privado do seu pedido NKATA"
    body = (
        f"Olá {primeiro_nome},\n\n"
        "Recebemos o seu pedido de entrada no NKATA.\n\n"
        "Este é o seu código privado de acompanhamento:\n"
        f"{pedido.token}\n\n"
        "Guarde o código e não o partilhe. Para consultar o andamento, use o "
        "mesmo email informado no pedido.\n\n"
        f"Acompanhar o pedido:\n{acompanhamento_url}\n\n"
        "Se não fez este pedido, ignore esta mensagem.\n\n"
        "NKATA\nRelações sérias começam com intenções claras."
    )
    return subject, body


def _send_status_email(pedido):
    subject, body = build_access_status_email(pedido)
    if not subject or not body or not pedido.email:
        return

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pedido.email],
        fail_silently=True,
    )


def send_access_receipt_email(pedido):
    """Envia o código sem propagar falhas do fornecedor de email à API."""
    if not pedido.email:
        return
    subject, body = build_access_receipt_email(pedido)
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[pedido.email],
        fail_silently=True,
    )


@receiver(pre_save, sender=PedidoEntrada)
def remember_previous_access_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._nkata_previous_status = None
        return

    previous = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    instance._nkata_previous_status = previous


@receiver(post_save, sender=PedidoEntrada)
def notify_access_status_change(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: send_access_receipt_email(instance))
        return

    previous = getattr(instance, "_nkata_previous_status", None)
    if previous == instance.status or instance.status not in NOTIFIABLE_STATUSES:
        return

    # Só envia depois do commit da alteração, evitando emails de operações revertidas.
    transaction.on_commit(lambda: _send_status_email(instance))
