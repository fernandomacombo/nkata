from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .content_moderation_admin import automatic_review_panel, automatic_risk_badge
from .moment_credit_service import moderate_moment
from .wallet_service import WalletError
from .moments_models import MomentoNKATA


@admin.register(MomentoNKATA)
class MomentoNKATAAdmin(admin.ModelAdmin):
    change_form_template = "admin/entradas/momentonkata/change_form.html"

    list_display = (
        "perfil",
        "tipo_media",
        "visibilidade",
        "risco_automatico",
        "moderacao_status",
        "criado_em",
        "expira_em",
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
        "texto",
    )
    readonly_fields = (
        "perfil",
        "usuario",
        "tipo_media",
        "visibilidade",
        "texto",
        "moderacao_status",
        "moderacao_motivo",
        "criado_em",
        "expira_em",
        "moderado_em",
        "media_privada",
        "analise_automatica",
        "regras_moderacao",
    )
    actions = (
        "aprovar_momentos",
        "rejeitar_momentos",
        "rejeitar_e_pausar_perfis",
    )
    fieldsets = (
        ("Conteúdo", {
            "fields": (
                "perfil",
                "usuario",
                "tipo_media",
                "texto",
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
                "expira_em",
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
            '<a href="/api/momentos/{}/media/" target="_blank" '
            'style="display:inline-block;padding:8px 12px;border-radius:8px;'
            'background:#7d2638;color:white;font-weight:700;text-decoration:none;">'
            'Abrir media privada para revisão</a>',
            obj.pk,
        )

    media_privada.short_description = "Ficheiro para revisão"

    def risco_automatico(self, obj):
        return automatic_risk_badge("MOMENTO", obj.pk)

    risco_automatico.short_description = "Risco automático"

    def analise_automatica(self, obj):
        return automatic_review_panel("MOMENTO", obj.pk)

    analise_automatica.short_description = "Pré-moderação automática"

    def regras_moderacao(self, obj):
        return mark_safe(
            "<div style='max-width:680px;line-height:1.65'>"
            "<strong>Não aprovar:</strong> nudez ou conteúdo sexual explícito; "
            "oferta/solicitação de serviços sexuais ou prostituição; telefone, "
            "WhatsApp, email, @username, links ou QR codes; publicidade/vendas; "
            "ameaças, assédio ou conteúdo que exponha outra pessoa sem consentimento."
            "<br><br><strong>Violações graves ou repetidas:</strong> use "
            "<em>Rejeitar e pausar perfil</em> para retirar o perfil da descoberta "
            "até revisão da equipa."
            "</div>"
        )

    regras_moderacao.short_description = "Regras rápidas"

    def _aprovar(self, momento):
        return moderate_moment(momento.pk, action="approve")

    def _rejeitar(self, momento, grave=False):
        note = ("Conteúdo rejeitado por violação grave das regras da comunidade." if grave
                else "Conteúdo não aprovado por não estar de acordo com as regras dos Momentos NKATA.")
        return moderate_moment(momento.pk, action="severe" if grave else "reject", note=note)

    def _apply_decision(self, request, obj, action):
        try:
            if action == "approve":
                self._aprovar(obj)
                message = "Momento aprovado."
            else:
                _, refund = self._rejeitar(obj, grave=action == "severe")
                message = "Momento rejeitado."
                if refund:
                    message += f" Devolução registada: {refund.quantidade} créditos."
                if action == "severe":
                    message += " Perfil pausado para revisão."
            self.message_user(request, message, level="success" if action == "approve" else "warning")
            return True
        except WalletError as error:
            self.message_user(request, str(error), level="error")
            return False

    def response_change(self, request, obj):
        for button, action in (("_aprovar_momento", "approve"), ("_rejeitar_momento", "reject"),
                               ("_rejeitar_pausar_momento", "severe")):
            if button in request.POST:
                self._apply_decision(request, obj, action)
                return HttpResponseRedirect(request.path)
        return super().response_change(request, obj)

    @admin.action(description="Aprovar Momentos selecionados")
    def aprovar_momentos(self, request, queryset):
        for item in queryset.order_by("pk"):
            self._apply_decision(request, item, "approve")

    @admin.action(description="Rejeitar Momentos selecionados")
    def rejeitar_momentos(self, request, queryset):
        for item in queryset.order_by("pk"):
            self._apply_decision(request, item, "reject")

    @admin.action(description="Rejeitar e pausar perfil por violação grave")
    def rejeitar_e_pausar_perfis(self, request, queryset):
        for item in queryset.order_by("pk"):
            self._apply_decision(request, item, "severe")
