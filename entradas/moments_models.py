from datetime import timedelta

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone

from .models import PerfilNKATA


MOMENT_LIFETIME_HOURS = 24
PRIVATE_MOMENT_STORAGE = FileSystemStorage(
    location=settings.BASE_DIR / "private_media" / "moments",
    base_url=None,
)


def moment_expires_at():
    return timezone.now() + timedelta(hours=MOMENT_LIFETIME_HOURS)


class MomentoNKATA(models.Model):
    MEDIA_CHOICES = [
        ("TEXTO", "Frase NKATA"),
        ("IMAGEM", "Imagem"),
        ("VIDEO", "Vídeo"),
    ]
    VISIBILITY_CHOICES = [
        ("TODOS", "Todos os membros"),
        ("MATCHES", "Apenas matches"),
    ]
    MODERATION_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("APROVADO", "Aprovado"),
        ("REJEITADO", "Rejeitado"),
    ]

    perfil = models.ForeignKey(
        PerfilNKATA,
        on_delete=models.CASCADE,
        related_name="momentos_nkata",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="momentos_nkata",
    )
    # O texto é preenchido apenas a partir de frases predefinidas no backend.
    # Texto livre não é aceite pela API dos Momentos.
    texto = models.CharField(max_length=500, blank=True)
    media = models.FileField(
        storage=PRIVATE_MOMENT_STORAGE,
        upload_to="%Y/%m/%d/",
        blank=True,
    )
    tipo_media = models.CharField(max_length=12, choices=MEDIA_CHOICES, default="TEXTO")
    visibilidade = models.CharField(
        max_length=12,
        choices=VISIBILITY_CHOICES,
        default="TODOS",
    )
    moderacao_status = models.CharField(
        max_length=12,
        choices=MODERATION_CHOICES,
        default="PENDENTE",
        db_index=True,
    )
    moderacao_motivo = models.CharField(max_length=240, blank=True)
    moderado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    expira_em = models.DateTimeField(default=moment_expires_at, db_index=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_momentonakata"
        managed = False
        ordering = ["-criado_em"]
        verbose_name = "Momento NKATA"
        verbose_name_plural = "Momentos NKATA"

    def __str__(self):
        return f"Momento de {self.perfil.nome_publico}"

    @property
    def ativo(self):
        return (
            self.moderacao_status == "APROVADO"
            and self.expira_em > timezone.now()
        )


class ReacaoMomentoNKATA(models.Model):
    REACTION_CHOICES = [
        ("CORACAO", "Gostei"),
        ("FLOR", "Flor"),
        ("APLAUSO", "Bonito"),
    ]

    momento = models.ForeignKey(
        MomentoNKATA,
        on_delete=models.CASCADE,
        related_name="reacoes_nkata",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reacoes_momentos_nkata",
    )
    tipo = models.CharField(max_length=16, choices=REACTION_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_reacaomomentonakata"
        managed = False
        ordering = ["-atualizado_em"]
        verbose_name = "Reação a Momento NKATA"
        verbose_name_plural = "Reações a Momentos NKATA"
        constraints = [
            models.UniqueConstraint(
                fields=["momento", "usuario"],
                name="nkata_reacao_unica_por_momento_usuario",
            )
        ]
        indexes = [
            models.Index(
                fields=["momento", "tipo"],
                name="nkata_moment_react_idx",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} em {self.momento_id} por {self.usuario_id}"
