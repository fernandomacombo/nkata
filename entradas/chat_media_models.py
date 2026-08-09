from django.conf import settings
from django.db import models

from .models import MatchPerfil
from .storage_backends import private_content_storage


class MensagemAudioMatchNKATA(models.Model):
    match = models.ForeignKey(
        MatchPerfil,
        on_delete=models.CASCADE,
        related_name="mensagens_audio_nkata",
    )
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensagens_audio_nkata_enviadas",
    )
    audio = models.FileField(
        storage=private_content_storage,
        upload_to="chat/%Y/%m/%d/",
    )
    duracao_segundos = models.PositiveSmallIntegerField(default=0)
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_mensagemaudiomatchnkata"
        managed = False
        ordering = ["criado_em", "id"]
        verbose_name = "Nota de voz NKATA"
        verbose_name_plural = "Notas de voz NKATA"
        indexes = [
            models.Index(
                fields=["match", "criado_em"],
                name="nkata_chat_audio_match_idx",
            ),
            models.Index(
                fields=["match", "lida"],
                name="nkata_chat_audio_read_idx",
            ),
        ]

    def __str__(self):
        return f"Nota de voz no match {self.match_id} — {self.criado_em:%d/%m/%Y %H:%M}"
