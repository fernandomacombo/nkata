from django.conf import settings
from django.db import models


class NotificacaoNKATA(models.Model):
    TIPO_CHOICES = [
        ("INTERESSE", "Novo interesse"),
        ("SINAL", "Novo sinal"),
        ("MOMENTO", "Reação em Momento"),
        ("PUBLICACAO", "Reação em Publicação"),
        ("MATCH", "Novo match"),
        ("MENSAGEM", "Nova mensagem"),
        ("EQUIPA", "Aviso da equipa"),
    ]

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificacoes_nkata",
    )
    ator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes_nkata_criadas",
    )
    perfil = models.ForeignKey(
        "entradas.PerfilNKATA",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes",
    )
    match = models.ForeignKey(
        "entradas.MatchPerfil",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificacoes",
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=120)
    texto = models.CharField(max_length=320)
    chave = models.CharField(max_length=120)
    lida = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizado_em"]
        verbose_name = "Notificação NKATA"
        verbose_name_plural = "Notificações NKATA"
        constraints = [
            models.UniqueConstraint(
                fields=["destinatario", "chave"],
                name="notificacao_unica_por_destinatario_e_chave",
            )
        ]
        indexes = [
            models.Index(
                fields=["destinatario", "lida", "atualizado_em"],
                name="nkata_notif_user_read_idx",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} para {self.destinatario}"
