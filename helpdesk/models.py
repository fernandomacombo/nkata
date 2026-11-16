import uuid
from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        ACCOUNT = "conta", "Conta e acesso"
        IDENTITY = "identidade", "Verificação de identidade"
        PAYMENT = "pagamentos", "Pagamentos e pacotes"
        MESSAGES = "mensagens", "Mensagens e momentos"
        SAFETY = "seguranca", "Segurança e denúncias"
        OTHER = "outro", "Outro assunto"

    class Status(models.TextChoices):
        OPEN = "aberto", "Aberto"
        REVIEW = "em_analise", "Em análise"
        WAITING = "aguarda_resposta", "A aguardar resposta"
        RESOLVED = "resolvido", "Resolvido"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="nkata_support_tickets")
    email = models.EmailField()
    category = models.CharField(max_length=24, choices=Category.choices)
    subject = models.CharField(max_length=140)
    description = models.TextField(max_length=4000)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.OPEN, db_index=True)
    internal_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Pedido de suporte"
        verbose_name_plural = "Pedidos de suporte"

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"
