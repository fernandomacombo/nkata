from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .content_moderation_service import record_human_decision
from .models import PerfilNKATA
from .post_safety_models import DenunciaPublicacaoNKATA


@admin.register(DenunciaPublicacaoNKATA)
class DenunciaPublicacaoNKATAAdmin(admin.ModelAdmin):
    list_display = (
        "publicacao_link",
        "autor_publicacao",
        "motivo",
        "estado",
        "denunciante",
        "criado_em",
    )
    list_filter = ("estado", "motivo", "criado_em")
    search_fields = (
        "publicacao__perfil__nome_publico",
        "publicacao__usuario__email",
        "denunciante__email",
    )
    readonly_fields = (
        "publicacao_link",
        "autor_publicacao",
        "denunciante",
        "motivo",
        "estado",
        "criado_em",
        "analisado_em",
    )
    fields = (
        "publicacao_link",
        "autor_publicacao",
        "denunciante",
        "motivo",
        "estado",
        "criado_em",
        "analisado_em",
    )
    actions = (
        "marcar_analisadas",
        "retirar_publicacoes",
        "retirar_e_pausar_perfis",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Publicação")
    def publicacao_link(self, obj):
        return format_html(
            '<a href="/admin/entradas/publicacaonkata/{}/change/">Abrir publicação #{}</a>',
            obj.publicacao_id,
            obj.publicacao_id,
        )

    @admin.display(description="Autor")
    def autor_publicacao(self, obj):
        return obj.publicacao.perfil.nome_publico

    @admin.action(description="Marcar denúncias selecionadas como analisadas")
    def marcar_analisadas(self, request, queryset):
        updated = queryset.update(
            estado="ANALISADA",
            analisado_em=timezone.now(),
        )
        self.message_user(request, f"{updated} denúncia/denúncias marcada(s) como analisada(s).")

    @admin.action(description="Retirar publicações denunciadas do feed")
    def retirar_publicacoes(self, request, queryset):
        publication_ids = list(queryset.values_list("publicacao_id", flat=True).distinct())
        now = timezone.now()
        publications = queryset.model._meta.get_field("publicacao").remote_field.model.objects.filter(
            id__in=publication_ids
        )
        removed = publications.update(
            moderacao_status="REJEITADO",
            moderacao_motivo="Publicação retirada após análise de denúncia da comunidade.",
            moderado_em=now,
        )
        for content_id in publication_ids:
            record_human_decision("PUBLICACAO", content_id, "REJEITADO")
        queryset.update(estado="ANALISADA", analisado_em=now)
        self.message_user(request, f"{removed} publicação/publicações retirada(s) do feed.")

    @admin.action(description="Retirar publicação e pausar perfil por violação grave")
    def retirar_e_pausar_perfis(self, request, queryset):
        publication_ids = list(queryset.values_list("publicacao_id", flat=True).distinct())
        profile_ids = list(queryset.values_list("publicacao__perfil_id", flat=True).distinct())
        now = timezone.now()
        publication_model = queryset.model._meta.get_field("publicacao").remote_field.model
        removed = publication_model.objects.filter(id__in=publication_ids).update(
            moderacao_status="REJEITADO",
            moderacao_motivo="Publicação retirada por violação grave após denúncia.",
            moderado_em=now,
        )
        for content_id in publication_ids:
            record_human_decision("PUBLICACAO", content_id, "GRAVE")
        paused = PerfilNKATA.objects.filter(id__in=profile_ids).exclude(
            status="BLOQUEADO"
        ).update(status="PAUSADO", visivel=False)
        queryset.update(estado="ANALISADA", analisado_em=now)
        self.message_user(
            request,
            f"{removed} publicação/publicações retirada(s) e {paused} perfil/perfis pausado(s).",
        )
