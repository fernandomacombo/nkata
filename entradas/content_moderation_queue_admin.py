from django.contrib import admin
from django.utils.html import format_html

from .content_moderation_admin import automatic_risk_badge
from .content_moderation_models import AnaliseAutomaticaConteudoNKATA


@admin.register(AnaliseAutomaticaConteudoNKATA)
class AnaliseAutomaticaConteudoNKATAAdmin(admin.ModelAdmin):
    list_display = (
        "conteudo_link",
        "media_type",
        "risco",
        "status",
        "provider",
        "human_decision",
        "atualizado_em",
    )
    list_filter = (
        "risk_level",
        "status",
        "content_type",
        "media_type",
        "provider",
        "human_decision",
        "atualizado_em",
    )
    search_fields = (
        "content_id",
        "file_sha256",
        "notes",
        "model_name",
    )
    ordering = ("-atualizado_em",)

    readonly_fields = (
        "content_type",
        "content_id",
        "media_type",
        "provider",
        "model_name",
        "status",
        "risk_level",
        "flagged",
        "file_sha256",
        "media_bytes",
        "image_width",
        "image_height",
        "categories",
        "category_scores",
        "notes",
        "human_decision",
        "criado_em",
        "atualizado_em",
        "conteudo_link",
    )
    fieldsets = (
        ("Conteúdo", {
            "fields": (
                "conteudo_link",
                "content_type",
                "content_id",
                "media_type",
                "file_sha256",
                "media_bytes",
                "image_width",
                "image_height",
            )
        }),
        ("Pré-moderação", {
            "fields": (
                "provider",
                "model_name",
                "status",
                "risk_level",
                "flagged",
                "categories",
                "category_scores",
                "notes",
            )
        }),
        ("Decisão humana", {
            "fields": ("human_decision",)
        }),
        ("Datas", {
            "fields": ("criado_em", "atualizado_em")
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Conteúdo")
    def conteudo_link(self, obj):
        if obj.content_type == "MOMENTO":
            return format_html(
                '<a href="/admin/entradas/momentonkata/{}/change/">Abrir Momento #{}</a>',
                obj.content_id,
                obj.content_id,
            )
        return format_html(
            '<a href="/admin/entradas/publicacaonkata/{}/change/">Abrir Publicação #{}</a>',
            obj.content_id,
            obj.content_id,
        )

    @admin.display(description="Risco automático")
    def risco(self, obj):
        return automatic_risk_badge(obj.content_type, obj.content_id)
