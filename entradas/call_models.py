from django.conf import settings
from django.db import models

from .models import MatchPerfil


class ChamadaMatchNKATA(models.Model):
    TIPO_AUDIO = "AUDIO"
    TIPO_VIDEO = "VIDEO"
    TIPO_CHOICES = [
        (TIPO_AUDIO, "Chamada de áudio"),
        (TIPO_VIDEO, "Videochamada"),
    ]

    ESTADO_CHAMANDO = "CHAMANDO"
    ESTADO_CONECTANDO = "CONECTANDO"
    ESTADO_ATIVA = "ATIVA"
    ESTADO_RECUSADA = "RECUSADA"
    ESTADO_TERMINADA = "TERMINADA"
    ESTADO_PERDIDA = "PERDIDA"
    ESTADO_FALHOU = "FALHOU"
    ESTADO_CHOICES = [
        (ESTADO_CHAMANDO, "A chamar"),
        (ESTADO_CONECTANDO, "A conectar"),
        (ESTADO_ATIVA, "Ativa"),
        (ESTADO_RECUSADA, "Recusada"),
        (ESTADO_TERMINADA, "Terminada"),
        (ESTADO_PERDIDA, "Não atendida"),
        (ESTADO_FALHOU, "Falhou"),
    ]

    match = models.ForeignKey(
        MatchPerfil,
        on_delete=models.CASCADE,
        related_name="chamadas_nkata",
    )
    iniciador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chamadas_nkata_iniciadas",
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES)
    estado = models.CharField(
        max_length=16,
        choices=ESTADO_CHOICES,
        default=ESTADO_CHAMANDO,
        db_index=True,
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    atendida_em = models.DateTimeField(null=True, blank=True)
    terminada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "entradas_chamadamatchnkata"
        ordering = ["-criada_em"]
        indexes = [
            models.Index(fields=["match", "estado"], name="nk_call_match_state_idx"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.pk} — {self.get_estado_display()}"


class SinalChamadaNKATA(models.Model):
    TIPO_OFFER = "OFFER"
    TIPO_ANSWER = "ANSWER"
    TIPO_ICE = "ICE"
    TIPO_CHOICES = [
        (TIPO_OFFER, "Oferta SDP"),
        (TIPO_ANSWER, "Resposta SDP"),
        (TIPO_ICE, "Candidato ICE"),
    ]

    chamada = models.ForeignKey(
        ChamadaMatchNKATA,
        on_delete=models.CASCADE,
        related_name="sinais",
    )
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sinais_chamada_nkata",
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES)
    payload = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "entradas_sinalchamadankata"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["chamada", "id"], name="nk_call_signal_idx"),
        ]

    def __str__(self):
        return f"{self.tipo} — chamada #{self.chamada_id}"
