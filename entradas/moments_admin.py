from datetime import timedelta

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import PerfilNKATA
from .moments_models import MOMENT_LIFETIME_HOURS, MomentoNKATA


@admin.register(MomentoNKATA)
class MomentoNKATAAdmin(admin.ModelAdmin):
    change_form_template = "admin/entradas/momentonkata/change_form.html"

    list_display = (
        "perfil",
        "tipo_media",
        "visibilidade",
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

    def regras_moderacao(self, obj):
        # HTML totalmente estático e controlado pelo código do NKATA.
        # No Django 6, format_html() exige args/kwargs; como não existe nenhum
        # dado dinâmico aqui, mark_safe() é a opção correta e mais simples.
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
        now = timezone.now()
        momento.moderacao_status = "APROVADO"
        momento.moderacao_motivo = ""
        momento.moderado_em = now
        momento.expira_em = now + timedelta(hours=MOMENT_LIFETIME_HOURS)
        momento.save(update_fields=[
            "moderacao_status",
            "moderacao_motivo",
            "moderado_em",
            "expira_em",
        ])

    def _rejeitar(self, momento, grave=False):
        momento.moderacao_status = "REJEITADO"
        momento.moderacao_motivo = (
            "Conteúdo rejeitado por violação grave das regras da comunidade."
            if grave
            else "Conteúdo não aprovado por não estar de acordo com as regras dos Momentos NKATA."
        )
        momento.moderado_em = timezone.now()
        momento.save(update_fields=[
            "moderacao_status",
            "moderacao_motivo",
            "moderado_em",
        ])

        if grave:
            PerfilNKATA.objects.filter(pk=momento.perfil_id).exclude(
                status="BLOQUEADO"
            ).update(status="PAUSADO", visivel=False)

    def response_change(self, request, obj):
        if "_aprovar_momento" in request.POST:
            self._aprovar(obj)
            self.message_user(
                request,
                "Momento aprovado. As 24 horas começam a contar agora.",
                level="success",
            )
            return HttpResponseRedirect(request.path)

        if "_rejeitar_momento" in request.POST:
            self._rejeitar(obj)
            self.message_user(
                request,
                "Momento rejeitado e mantido fora da comunidade.",
                level="warning",
            )
            return HttpResponseRedirect(request.path)

        if "_rejeitar_pausar_momento" in request.POST:
            self._rejeitar(obj, grave=True)
            self.message_user(
                request,
                "Momento rejeitado e perfil pausado para revisão da equipa.",
                level="warning",
            )
            return HttpResponseRedirect(request.path)

        return super().response_change(request, obj)

    @admin.action(description="Aprovar Momentos selecionados")
    def aprovar_momentos(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(
            moderacao_status="APROVADO",
            moderacao_motivo="",
            moderado_em=now,
            expira_em=now + timedelta(hours=MOMENT_LIFETIME_HOURS),
        )
        self.message_user(
            request,
            f"{updated} Momento(s) aprovado(s). As 24 horas começam agora.",
        )

    @admin.action(description="Rejeitar Momentos selecionados")
    def rejeitar_momentos(self, request, queryset):
        updated = queryset.update(
            moderacao_status="REJEITADO",
            moderacao_motivo=(
                "Conteúdo não aprovado por não estar de acordo com as regras dos Momentos NKATA."
            ),
            moderado_em=timezone.now(),
        )
        self.message_user(request, f"{updated} Momento(s) rejeitado(s).")

    @admin.action(description="Rejeitar e pausar perfil por violação grave")
    def rejeitar_e_pausar_perfis(self, request, queryset):
        profile_ids = list(queryset.values_list("perfil_id", flat=True).distinct())
        rejected = queryset.update(
            moderacao_status="REJEITADO",
            moderacao_motivo=(
                "Conteúdo rejeitado por violação grave das regras da comunidade."
            ),
            moderado_em=timezone.now(),
        )
        paused = PerfilNKATA.objects.filter(id__in=profile_ids).exclude(
            status="BLOQUEADO"
        ).update(
            status="PAUSADO",
            visivel=False,
        )
        self.message_user(
            request,
            f"{rejected} Momento(s) rejeitado(s) e {paused} perfil/perfis pausado(s).",
        )
