from django.conf import settings
from django.db import models

from .models import MatchPerfil


class EstadoConversaNKATA(models.Model):
    match = models.ForeignKey(
        MatchPerfil,
        on_delete=models.CASCADE,
        related_name="estados_realtime_nkata",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estados_conversa_nkata",
    )
    is_typing = models.BooleanField(default=False)
    typing_updated_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "entradas_estadoconversankata"
        constraints = [
            models.UniqueConstraint(
                fields=["match", "usuario"],
                name="estado_conversa_unico_match_usuario",
            )
        ]
        indexes = [
            models.Index(fields=["match", "last_seen_at"]),
        ]

    def __str__(self):
        return f"Estado conversa #{self.match_id} - user #{self.usuario_id}"
