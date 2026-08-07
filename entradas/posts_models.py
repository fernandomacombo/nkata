from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from .models import PerfilNKATA


PRIVATE_POST_STORAGE = FileSystemStorage(
    location=settings.BASE_DIR / "private_media" / "posts",
    base_url=None,
)


class PublicacaoNKATA(models.Model):
    MEDIA_CHOICES = [
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
        related_name="publicacoes_nkata",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="publicacoes_nkata",
    )
    media = models.FileField(
        storage=PRIVATE_POST_STORAGE,
        upload_to="%Y/%m/%d/",
    )
    tipo_media = models.CharField(max_length=12, choices=MEDIA_CHOICES)
    legenda = models.CharField(max_length=180, blank=True)
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
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_publicacaonkata"
        managed = False
        ordering = ["-criado_em"]
        verbose_name = "Publicação NKATA"
        verbose_name_plural = "Publicações NKATA"

    def __str__(self):
        return f"Publicação de {self.perfil.nome_publico}"


class ReacaoPublicacaoNKATA(models.Model):
    REACTION_CHOICES = [
        ("GOSTEI", "Gostei"),
        ("FLOR", "Flor"),
        ("APRECIAR", "Apreciar"),
    ]

    publicacao = models.ForeignKey(
        PublicacaoNKATA,
        on_delete=models.CASCADE,
        related_name="reacoes_nkata",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reacoes_publicacoes_nkata",
    )
    tipo = models.CharField(max_length=16, choices=REACTION_CHOICES)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_reacaopublicacaonkata"
        managed = False
        ordering = ["-atualizado_em"]
        verbose_name = "Reação a Publicação NKATA"
        verbose_name_plural = "Reações a Publicações NKATA"
        constraints = [
            models.UniqueConstraint(
                fields=["publicacao", "usuario"],
                name="nkata_reacao_unica_publicacao_usuario",
            )
        ]
        indexes = [
            models.Index(
                fields=["publicacao", "tipo"],
                name="nkata_post_react_idx",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} em {self.publicacao_id} por {self.usuario_id}"
