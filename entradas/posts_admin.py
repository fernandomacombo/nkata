from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .content_moderation_admin import automatic_review_panel, automatic_risk_badge
from .content_moderation_service import record_human_decision
from .models import PerfilNKATA
from .posts_models import PublicacaoNKATA


@admin.register(PublicacaoNKATA)
class PublicacaoNKATAAdmin(admin.ModelAdmin):
    change_form_template = "admin/entradas/publicacaonkata/change_form.html"

    list_display = (
        "perfil",
        "tipo_media",
        "visibilidade",
        "risco_automatico",
        "moderacao_status",
        "criado_em",
    )
    list_filter = (
        "moderacao_status",
        "tipo_media",
        "visibilidade",
        "criado_em",
    )
    search_fields = (
        "perfil__nome_publico",
        "perfil__pedido__nome_completo",
        "perfil__pedido__email",
        "usuario__email",
        "legenda",
    )
    readonly_fields = (
        "perfil",
        "usuario",
        "tipo_media",
        "legenda",
        "visibilidade",
        "moderacao_status",
        "moderacao_motivo",
        "moderado_em",
        "criado_em",
        "atualizado_em",
        "media_privada",
        "analise_automatica",
        "regras_moderacao",
    )
    actions = (
        "aprovar_publicacoes",
        "rejeitar_publicacoes",
        "rejeitar_e_pausar_perfis",
    )
    fieldsets = (
        ("Conteúdo", {
            "fields": (
                "perfil",
                "usuario",
                "tipo_media",
                "legenda",
                "media_privada",
                "visibilidade",
            )
        }),
        ("Moderação", {
            "fields": (
                "analise_automatica",
                "moderacao_status",
                "moderacao_motivo",
                "moderado_em",
                "regras_moderacao",
            )
        }),
        ("Datas", {
            "fields": (
                "criado_em",
                "atualizado_em",
            )
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def media_privada(self, obj):
        if not obj.pk or not obj.media:
            return "Sem fotografia/vídeo."
        return format_html(
            '<a href="/api/publicacoes/{}/media/" target="_blank" '
            'style="display:inline-block;padding:8px 12px;border-radius:8px;'
            'background:#7d2638;color:white;font-weight:700;text-decoration:none;">'
            'Abrir media privada para revisão</a>',
            obj.pk,
        )

    media_privada.short_description = "Ficheiro para revisão"

    def risco_automatico(self, obj):
        return automatic_risk_badge("PUBLICACAO", obj.pk)

    risco_automatico.short_description = "Risco automático"

    def analise_automatica(self, obj):
        return automatic_review_panel("PUBLICACAO", obj.pk)

    analise_automatica.short_description = "Pré-moderação automática"

    def regras_moderacao(self, obj):
        return mark_safe(
            "<div style='max-width:700px;line-height:1.65'>"
            "<strong>Não aprovar:</strong> nudez ou conteúdo sexual explícito; "
            "oferta ou solicitação de serviços sexuais; prostituição; telefone, "
            "WhatsApp, email, @username, links ou QR codes visíveis na media; "
            "publicidade, vendas, conteúdo enganoso, ameaças, assédio ou exposição "
            "de terceiros sem consentimento."
            "<br><br><strong>Violações graves ou repetidas:</strong> use "
            "<em>Rejeitar e pausar perfil</em> para retirar o perfil da descoberta "
            "até revisão da equipa."
            "</div>"
        )

    regras_moderacao.short_description = "Regras rápidas"

    def _aprovar(self, publicacao):
        publicacao.moderacao_status = "APROVADO"
        publicacao.moderacao_motivo = ""
        publicacao.moderado_em = timezone.now()
        publicacao.save(update_fields=[
            "moderacao_status",
            "moderacao_motivo",
            "moderado_em",
            "atualizado_em",
        ])
        record_human_decision("PUBLICACAO", publicacao.pk, "APROVADO")

    def _rejeitar(self, publicacao, grave=False):
        publicacao.moderacao_status = "REJEITADO"
        publicacao.moderacao_motivo = (
            "Conteúdo rejeitado por violação grave das regras da comunidade."
            if grave
            else "Conteúdo não aprovado por não estar de acordo com as regras das Publicações NKATA."
        )
        publicacao.moderado_em = timezone.now()
        publicacao.save(update_fields=[
            "moderacao_status",
            "moderacao_motivo",
            "moderado_em",
            "atualizado_em",
        ])
        record_human_decision(
            "PUBLICACAO",
            publicacao.pk,
            "GRAVE" if grave else "REJEITADO",
        )

        if grave:
            PerfilNKATA.objects.filter(pk=publicacao.perfil_id).exclude(
                status="BLOQUEADO"
            ).update(status="PAUSADO", visivel=False)

    def response_change(self, request, obj):
        if "_aprovar_publicacao" in request.POST:
            self._aprovar(obj)
            self.message_user(
                request,
                "Publicação aprovada e disponível no feed.",
                level="success",
            )
            return HttpResponseRedirect(request.path)

        if "_rejeitar_publicacao" in request.POST:
            self._rejeitar(obj)
            self.message_user(
                request,
                "Publicação rejeitada e mantida fora do feed.",
                level="warning",
            )
            return HttpResponseRedirect(request.path)

        if "_rejeitar_pausar_publicacao" in request.POST:
            self._rejeitar(obj, grave=True)
            self.message_user(
                request,
                "Publicação rejeitada e perfil pausado para revisão da equipa.",
                level="warning",
            )
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @admin.action(description="Aprovar Publicações selecionadas")
    def aprovar_publicacoes(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        updated = queryset.update(
            moderacao_status="APROVADO",
            moderacao_motivo="",
            moderado_em=timezone.now(),
        )
        for content_id in ids:
            record_human_decision("PUBLICACAO", content_id, "APROVADO")
        self.message_user(request, f"{updated} publicação/publicações aprovada(s).")

    @admin.action(description="Rejeitar Publicações selecionadas")
    def rejeitar_publicacoes(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        updated = queryset.update(
            moderacao_status="REJEITADO",
            moderacao_motivo=(
                "Conteúdo não aprovado por não estar de acordo com as regras das Publicações NKATA."
            ),
            moderado_em=timezone.now(),
        )
        for content_id in ids:
            record_human_decision("PUBLICACAO", content_id, "REJEITADO")
        self.message_user(request, f"{updated} publicação/publicações rejeitada(s).")

    @admin.action(description="Rejeitar e pausar perfil por violação grave")
    def rejeitar_e_pausar_perfis(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        profile_ids = list(queryset.values_list("perfil_id", flat=True).distinct())
        rejected = queryset.update(
            moderacao_status="REJEITADO",
            moderacao_motivo=(
                "Conteúdo rejeitado por violação grave das regras da comunidade."
            ),
            moderado_em=timezone.now(),
        )
        for content_id in ids:
            record_human_decision("PUBLICACAO", content_id, "GRAVE")
        paused = PerfilNKATA.objects.filter(id__in=profile_ids).exclude(
            status="BLOQUEADO"
        ).update(status="PAUSADO", visivel=False)
        self.message_user(
            request,
            f"{rejected} publicação/publicações rejeitada(s) e {paused} perfil/perfis pausado(s).",
        )
