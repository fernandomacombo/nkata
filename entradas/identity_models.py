import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from .storage_backends import identity_media_storage


def nkata_id_expires_at():
    minutes = int(getattr(settings, "NKATA_ID_SESSION_MINUTES", 30))
    return timezone.now() + timedelta(minutes=max(10, min(minutes, 120)))


def pedido_tem_identidade_verificada(pedido):
    """Usa o NKATA ID novo e mantém perfis legados aprovados compatíveis."""
    verification = getattr(pedido, "verificacao_identidade", None)
    if verification is None:
        return getattr(pedido, "status", "") == "APROVADO"
    return verification.status == "APROVADA"


class VerificacaoIdentidadeNKATA(models.Model):
    STATUS_CHOICES = [
        ("INICIADA", "Iniciada"),
        ("EM_CAPTURA", "Em captura"),
        ("A_ANALISAR", "A analisar"),
        ("APROVADA", "Aprovada automaticamente"),
        ("REVISAO", "Revisão humana necessária"),
        ("REPETIR", "Nova captura necessária"),
        ("REJEITADA", "Rejeitada"),
        ("EXPIRADA", "Expirada"),
    ]
    RISK_CHOICES = [
        ("INDEFINIDO", "Indefinido"),
        ("BAIXO", "Baixo"),
        ("MEDIO", "Médio"),
        ("ALTO", "Alto"),
    ]
    DECISION_CHOICES = [
        ("", "Sem decisão"),
        ("AUTOMATICA", "Automática"),
        ("HUMANA", "Humana"),
    ]
    CAPTURE_FIELDS = (
        "bi_frente",
        "bi_verso",
        "selfie_ao_vivo",
        "selfie_desafio",
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pedido = models.OneToOneField(
        "entradas.PedidoEntrada",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verificacao_identidade",
    )
    email_hash = models.CharField(max_length=64, db_index=True)
    idade_declarada = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="INICIADA",
        db_index=True,
    )
    risco = models.CharField(
        max_length=12,
        choices=RISK_CHOICES,
        default="INDEFINIDO",
        db_index=True,
    )
    pontuacao_risco = models.PositiveSmallIntegerField(default=0)
    etapa_atual = models.CharField(max_length=24, default="bi_frente")
    desafio_selfie = models.CharField(max_length=120)
    aceita_biometria = models.BooleanField(default=False)
    usar_foto_verificada = models.BooleanField(default=False)

    bi_frente = models.ImageField(
        storage=identity_media_storage,
        upload_to="nkata-id/documentos/%Y/%m/%d/",
        blank=True,
    )
    bi_verso = models.ImageField(
        storage=identity_media_storage,
        upload_to="nkata-id/documentos/%Y/%m/%d/",
        blank=True,
    )
    selfie_ao_vivo = models.ImageField(
        storage=identity_media_storage,
        upload_to="nkata-id/selfies/%Y/%m/%d/",
        blank=True,
    )
    selfie_desafio = models.ImageField(
        storage=identity_media_storage,
        upload_to="nkata-id/selfies/%Y/%m/%d/",
        blank=True,
    )

    verificacoes_imagem = models.JSONField(default=dict, blank=True)
    sinais_risco = models.JSONField(default=dict, blank=True)
    documento_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    selfie_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    provedor_biometrico = models.CharField(max_length=40, default="qualidade_local")
    correspondencia_facial = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    vivacidade_confirmada = models.BooleanField(default=False)
    decisao_origem = models.CharField(
        max_length=12,
        choices=DECISION_CHOICES,
        blank=True,
    )
    nota_interna = models.TextField(blank=True)
    analisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verificacoes_nkata_id_analisadas",
    )
    analisado_em = models.DateTimeField(null=True, blank=True)
    consentido_em = models.DateTimeField(default=timezone.now)
    expira_em = models.DateTimeField(default=nkata_id_expires_at, db_index=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Verificação NKATA ID"
        verbose_name_plural = "Verificações NKATA ID"
        ordering = ["-atualizado_em"]

    def __str__(self):
        return f"NKATA ID {str(self.token)[:8]} — {self.get_status_display()}"

    @property
    def expirada(self):
        return self.expira_em <= timezone.now()

    @property
    def capturas_completas(self):
        return all(bool(getattr(self, field_name)) for field_name in self.CAPTURE_FIELDS)

    @property
    def pode_anexar_ao_pedido(self):
        return self.status in {"APROVADA", "REVISAO"} and self.capturas_completas
