from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .identity_models import VerificacaoIdentidadeNKATA, nkata_id_expires_at


@admin.register(VerificacaoIdentidadeNKATA)
class VerificacaoIdentidadeNKATAAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_curto",
        "pedido",
        "status",
        "risco",
        "pontuacao_risco",
        "correspondencia_facial",
        "vivacidade_confirmada",
        "atualizado_em",
    )
    list_filter = (
        "status",
        "risco",
        "decisao_origem",
        "vivacidade_confirmada",
        "criado_em",
    )
    search_fields = (
        "token",
        "pedido__nome_completo",
        "pedido__email",
    )
    readonly_fields = (
        "token",
        "email_hash",
        "bi_frente_preview",
        "bi_verso_preview",
        "selfie_ao_vivo_preview",
        "selfie_desafio_preview",
        "verificacoes_imagem",
        "sinais_risco",
        "criado_em",
        "atualizado_em",
        "consentido_em",
    )
    actions = (
        "aprovar_verificacoes",
        "pedir_nova_captura",
        "rejeitar_verificacoes",
    )
    fieldsets = (
        ("Sessão NKATA ID", {"fields": (
            "token", "pedido", "status", "etapa_atual", "expira_em",
            "aceita_biometria", "usar_foto_verificada",
        )}),
        ("Evidências privadas", {"fields": (
            "bi_frente_preview", "bi_verso_preview",
            "selfie_ao_vivo_preview", "selfie_desafio_preview",
        )}),
        ("Análise automática", {"fields": (
            "risco", "pontuacao_risco", "provedor_biometrico",
            "correspondencia_facial", "vivacidade_confirmada",
            "verificacoes_imagem", "sinais_risco",
        )}),
        ("Decisão", {"fields": (
            "decisao_origem", "nota_interna", "analisado_por", "analisado_em",
        )}),
        ("Datas e privacidade", {"fields": (
            "email_hash", "consentido_em", "criado_em", "atualizado_em",
        )}),
    )

    def codigo_curto(self, obj):
        return str(obj.token)[:8]

    codigo_curto.short_description = "Código"

    def _preview(self, obj, field_name):
        field = getattr(obj, field_name)
        if not field:
            return "Ainda não enviada"
        url = reverse(
            "entradas_api:nkata_id_media_admin",
            kwargs={"verification_id": obj.pk, "field_name": field_name},
        )
        return format_html(
            '<a href="{0}" target="_blank"><img src="{0}" '
            'style="max-width:260px;max-height:260px;object-fit:cover;'
            'border-radius:14px;border:1px solid #ddd;padding:4px;background:#fff" /></a>',
            url,
        )

    def bi_frente_preview(self, obj):
        return self._preview(obj, "bi_frente")

    def bi_verso_preview(self, obj):
        return self._preview(obj, "bi_verso")

    def selfie_ao_vivo_preview(self, obj):
        return self._preview(obj, "selfie_ao_vivo")

    def selfie_desafio_preview(self, obj):
        return self._preview(obj, "selfie_desafio")

    @admin.action(description="Aprovar identidade selecionada")
    def aprovar_verificacoes(self, request, queryset):
        queryset.update(
            status="APROVADA",
            risco="BAIXO",
            decisao_origem="HUMANA",
            analisado_por=request.user,
            analisado_em=timezone.now(),
        )

    @admin.action(description="Pedir nova captura")
    def pedir_nova_captura(self, request, queryset):
        for verification in queryset:
            for field_name in verification.CAPTURE_FIELDS:
                field = getattr(verification, field_name)
                if field:
                    field.delete(save=False)
            verification.status = "REPETIR"
            verification.risco = "INDEFINIDO"
            verification.pontuacao_risco = 0
            verification.etapa_atual = "bi_frente"
            verification.verificacoes_imagem = {}
            verification.sinais_risco = {}
            verification.documento_sha256 = ""
            verification.selfie_sha256 = ""
            verification.provedor_biometrico = "qualidade_local"
            verification.correspondencia_facial = None
            verification.vivacidade_confirmada = False
            verification.decisao_origem = "HUMANA"
            verification.analisado_por = request.user
            verification.analisado_em = timezone.now()
            verification.expira_em = nkata_id_expires_at()
            verification.save()

    @admin.action(description="Rejeitar identidade selecionada")
    def rejeitar_verificacoes(self, request, queryset):
        queryset.update(
            status="REJEITADA",
            risco="ALTO",
            decisao_origem="HUMANA",
            analisado_por=request.user,
            analisado_em=timezone.now(),
        )
