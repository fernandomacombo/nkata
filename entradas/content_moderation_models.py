from django.db import models


class AnaliseAutomaticaConteudoNKATA(models.Model):
    CONTENT_CHOICES = [
        ("MOMENTO", "Momento"),
        ("PUBLICACAO", "Publicação"),
    ]
    MEDIA_CHOICES = [
        ("IMAGEM", "Imagem"),
        ("VIDEO", "Vídeo"),
    ]
    STATUS_CHOICES = [
        ("REVISAO", "Revisão humana necessária"),
        ("BAIXO_RISCO", "Baixo risco"),
        ("ALTO_RISCO", "Risco elevado"),
        ("ERRO", "Análise indisponível"),
    ]
    RISK_CHOICES = [
        ("INDEFINIDO", "Indefinido"),
        ("BAIXO", "Baixo"),
        ("MEDIO", "Médio"),
        ("ALTO", "Alto"),
        ("CRITICO", "Crítico"),
    ]
    HUMAN_CHOICES = [
        ("", "Sem decisão"),
        ("APROVADO", "Aprovado"),
        ("REJEITADO", "Rejeitado"),
        ("GRAVE", "Rejeitado por violação grave"),
    ]

    content_type = models.CharField(max_length=16, choices=CONTENT_CHOICES)
    content_id = models.PositiveBigIntegerField()
    media_type = models.CharField(max_length=12, choices=MEDIA_CHOICES)

    provider = models.CharField(max_length=32, default="manual")
    model_name = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="REVISAO")
    risk_level = models.CharField(max_length=12, choices=RISK_CHOICES, default="INDEFINIDO")
    flagged = models.BooleanField(default=False)

    file_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    media_bytes = models.PositiveBigIntegerField(default=0)
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)

    categories = models.JSONField(default=dict, blank=True)
    category_scores = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    human_decision = models.CharField(max_length=12, choices=HUMAN_CHOICES, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "entradas"
        db_table = "entradas_analiseautomaticaconteudonkata"
        managed = False
        ordering = ["-atualizado_em"]
        verbose_name = "Análise automática de conteúdo NKATA"
        verbose_name_plural = "Análises automáticas de conteúdo NKATA"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "content_id"],
                name="nkata_auto_review_unique_content",
            )
        ]
        indexes = [
            models.Index(
                fields=["file_sha256", "human_decision"],
                name="nkata_auto_review_hash_idx",
            ),
            models.Index(
                fields=["status", "risk_level"],
                name="nkata_auto_review_risk_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()} #{self.content_id} — {self.get_risk_level_display()}"
