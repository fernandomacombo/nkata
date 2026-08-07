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
        ("TEXTO", "Texto"),
        ("IMAGEM", "Imagem"),
        ("VIDEO", "Vídeo"),
    ]
    VISIBILITY_CHOICES = [
        ("TODOS", "Todos os membros"),
        ("MATCHES", "Apenas matches"),
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
        return self.expira_em > timezone.now()
