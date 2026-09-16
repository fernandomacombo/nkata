from django.conf import settings
from django.db import models

from .posts_models import PublicacaoNKATA


class OcultacaoPublicacaoNKATA(models.Model):
    publicacao = models.ForeignKey(
        PublicacaoNKATA,
        on_delete=models.CASCADE,
        related_name="ocultacoes_nkata",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="publicacoes_ocultadas_nkata",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_ocultacaopublicacaonkata"
        managed = False
        verbose_name = "Publicação ocultada NKATA"
        verbose_name_plural = "Publicações ocultadas NKATA"
        constraints = [
            models.UniqueConstraint(
                fields=["publicacao", "usuario"],
                name="nkata_post_hide_unique_user",
            )
        ]

    def __str__(self):
        return f"Publicação {self.publicacao_id} ocultada por {self.usuario_id}"


class DenunciaPublicacaoNKATA(models.Model):
    MOTIVO_CHOICES = [
        ("NUDEZ_SEXUAL", "Nudez ou conteúdo sexual"),
        ("SERVICOS_SEXUAIS", "Serviços sexuais ou prostituição"),
        ("CONTACTOS_PUBLICIDADE", "Contactos, publicidade ou venda"),
        ("ASSEDIO", "Assédio, ameaça ou discurso ofensivo"),
        ("FRAUDE", "Fraude, perfil falso ou conteúdo enganoso"),
        ("PRIVACIDADE_TERCEIROS", "Exposição de terceiros sem consentimento"),
    ]
    ESTADO_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("ANALISADA", "Analisada"),
    ]

    publicacao = models.ForeignKey(
        PublicacaoNKATA,
        on_delete=models.CASCADE,
        related_name="denuncias_nkata",
    )
    denunciante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="denuncias_publicacoes_nkata",
    )
    motivo = models.CharField(max_length=32, choices=MOTIVO_CHOICES)
    estado = models.CharField(
        max_length=12,
        choices=ESTADO_CHOICES,
        default="PENDENTE",
        db_index=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    analisado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_denunciapublicacaonkata"
        managed = False
        ordering = ["-criado_em"]
        verbose_name = "Denúncia de Publicação NKATA"
        verbose_name_plural = "Denúncias de Publicações NKATA"
        constraints = [
            models.UniqueConstraint(
                fields=["publicacao", "denunciante"],
                name="nkata_post_report_unique_user",
            )
        ]
        indexes = [
            models.Index(
                fields=["estado", "criado_em"],
                name="nkata_post_report_state_idx",
            )
        ]

    def __str__(self):
        return f"Denúncia da publicação {self.publicacao_id}"
