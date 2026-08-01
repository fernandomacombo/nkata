from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    PedidoEntrada,
    QuestionarioEntrada,
    PerfilNKATA,
    AcaoPerfil,
    MensagemPerfil,
    DenunciaPerfil,
    MatchPerfil,
    MensagemMatch,
)


@admin.register(PedidoEntrada)
class PedidoEntradaAdmin(admin.ModelAdmin):
    list_display = (
        "nome_completo",
        "idade",
        "cidade",
        "genero",
        "objetivo",
        "status",
        "foto_preview_pequena",
        "criado_em",
    )

    list_filter = (
        "status",
        "genero",
        "objetivo",
        "cidade",
        "criado_em",
    )

    search_fields = (
        "nome_completo",
        "email",
        "telefone",
        "cidade",
    )

    readonly_fields = (
        "criado_em",
        "atualizado_em",
        "foto_perfil_preview",
        "foto_extra_1_preview",
        "foto_extra_2_preview",
        "foto_extra_3_preview",
        "bi_frente_preview",
        "bi_verso_preview",
        "selfie_com_bi_preview",
        "link_questionario",
    )

    actions = (
        "marcar_como_em_analise",
        "marcar_como_aprovado",
        "marcar_como_precisa_corrigir",
        "marcar_como_recusado",
        "marcar_como_bloqueado",
    )

    fieldsets = (
        ("Dados pessoais", {
            "fields": (
                "nome_completo",
                "email",
                "telefone",
                "idade",
                "cidade",
                "genero",
                "objetivo",
                "aceita_verificacao",
            )
        }),

        ("Fotos pessoais", {
            "fields": (
                "foto_perfil",
                "foto_perfil_preview",
                "foto_extra_1",
                "foto_extra_1_preview",
                "foto_extra_2",
                "foto_extra_2_preview",
                "foto_extra_3",
                "foto_extra_3_preview",
            )
        }),

        ("Documentos de verificação", {
            "fields": (
                "bi_frente",
                "bi_frente_preview",
                "bi_verso",
                "bi_verso_preview",
                "selfie_com_bi",
                "selfie_com_bi_preview",
            )
        }),

        ("Análise interna", {
            "fields": (
                "status",
                "observacao_admin",
                "link_questionario",
            )
        }),

        ("Datas", {
            "fields": (
                "criado_em",
                "atualizado_em",
            )
        }),
    )

    def foto_preview_pequena(self, obj):
        if obj.foto_perfil:
            return format_html(
                '<img src="{}" style="width:55px;height:55px;object-fit:cover;border-radius:50%;" />',
                obj.foto_perfil.url
            )

        return "Sem foto"

    foto_preview_pequena.short_description = "Foto"

    def imagem_preview(self, imagem):
        if imagem:
            return format_html(
                """
                <a href="{0}" target="_blank">
                    <img src="{0}" style="
                        max-width:260px;
                        max-height:260px;
                        object-fit:cover;
                        border-radius:14px;
                        border:1px solid #ddd;
                        padding:4px;
                        background:#fff;
                    " />
                </a>
                """,
                imagem.url
            )

        return "Nenhuma imagem enviada"

    def foto_perfil_preview(self, obj):
        return self.imagem_preview(obj.foto_perfil)

    foto_perfil_preview.short_description = "Pré-visualização da foto principal"

    def foto_extra_1_preview(self, obj):
        return self.imagem_preview(obj.foto_extra_1)

    foto_extra_1_preview.short_description = "Pré-visualização da foto adicional 1"

    def foto_extra_2_preview(self, obj):
        return self.imagem_preview(obj.foto_extra_2)

    foto_extra_2_preview.short_description = "Pré-visualização da foto adicional 2"

    def foto_extra_3_preview(self, obj):
        return self.imagem_preview(obj.foto_extra_3)

    foto_extra_3_preview.short_description = "Pré-visualização da foto adicional 3"

    def bi_frente_preview(self, obj):
        return self.imagem_preview(obj.bi_frente)

    bi_frente_preview.short_description = "Pré-visualização do BI - Frente"

    def bi_verso_preview(self, obj):
        return self.imagem_preview(obj.bi_verso)

    bi_verso_preview.short_description = "Pré-visualização do BI - Verso"

    def selfie_com_bi_preview(self, obj):
        return self.imagem_preview(obj.selfie_com_bi)

    selfie_com_bi_preview.short_description = "Pré-visualização da selfie com BI"

    def link_questionario(self, obj):
        if not obj.pk:
            return "Guarde o pedido primeiro."

        url = reverse("entradas:responder_questionario", kwargs={"token": obj.token})

        if obj.status != "APROVADO":
            return format_html(
                """
                <div style="line-height:1.6;">
                    <span style="color:#666;">
                        O link só deve ser enviado depois do pedido estar aprovado.
                    </span><br>
                    <a href="{}" target="_blank" style="font-weight:700;color:#c8102e;">
                        Abrir mesmo assim
                    </a>
                </div>
                """,
                url
            )

        return format_html(
            """
            <a href="{}" target="_blank" style="
                display:inline-flex;
                align-items:center;
                padding:8px 12px;
                border-radius:10px;
                background:#c8102e;
                color:#fff;
                font-weight:700;
                text-decoration:none;
            ">
                Abrir questionário aprovado
            </a>
            """,
            url
        )

    link_questionario.short_description = "Link do questionário"

    @admin.action(description="Marcar como em análise")
    def marcar_como_em_analise(self, request, queryset):
        queryset.update(status="EM_ANALISE")

    @admin.action(description="Aprovar pedidos selecionados")
    def marcar_como_aprovado(self, request, queryset):
        queryset.update(status="APROVADO")

    @admin.action(description="Marcar como precisa corrigir")
    def marcar_como_precisa_corrigir(self, request, queryset):
        queryset.update(status="PRECISA_CORRIGIR")

    @admin.action(description="Recusar pedidos selecionados")
    def marcar_como_recusado(self, request, queryset):
        queryset.update(status="RECUSADO")

    @admin.action(description="Bloquear pedidos selecionados")
    def marcar_como_bloqueado(self, request, queryset):
        queryset.update(status="BLOQUEADO")


@admin.register(QuestionarioEntrada)
class QuestionarioEntradaAdmin(admin.ModelAdmin):
    list_display = (
        "nome_do_pedido",
        "cidade_preferida",
        "faixa_etaria_preferida",
        "disponibilidade",
        "tem_filhos",
        "aceita_pessoa_com_filhos",
        "criado_em",
    )

    list_filter = (
        "disponibilidade",
        "tem_filhos",
        "aceita_pessoa_com_filhos",
        "criado_em",
    )

    search_fields = (
        "pedido__nome_completo",
        "pedido__email",
        "pedido__telefone",
        "cidade_preferida",
        "faixa_etaria_preferida",
    )

    readonly_fields = (
        "criado_em",
        "atualizado_em",
    )

    fieldsets = (
        ("Pedido relacionado", {
            "fields": (
                "pedido",
            )
        }),

        ("Respostas principais", {
            "fields": (
                "disponibilidade",
                "tem_filhos",
                "aceita_pessoa_com_filhos",
                "cidade_preferida",
                "faixa_etaria_preferida",
            )
        }),

        ("Textos do questionário", {
            "fields": (
                "sobre_si",
                "o_que_valoriza",
                "o_que_nao_aceita",
                "aceita_regras",
            )
        }),

        ("Datas", {
            "fields": (
                "criado_em",
                "atualizado_em",
            )
        }),
    )

    def nome_do_pedido(self, obj):
        return obj.pedido.nome_completo

    nome_do_pedido.short_description = "Nome"


@admin.register(PerfilNKATA)
class PerfilNKATAAdmin(admin.ModelAdmin):
    list_display = (
        "nome_publico",
        "cidade",
        "idade",
        "genero",
        "objetivo",
        "status",
        "visivel",
        "usuario",
        "criado_em",
    )

    list_filter = (
        "status",
        "visivel",
        "genero",
        "objetivo",
        "cidade",
        "criado_em",
    )

    search_fields = (
        "nome_publico",
        "cidade",
        "pedido__nome_completo",
        "pedido__email",
        "usuario__username",
        "usuario__email",
    )

    readonly_fields = (
        "pedido",
        "usuario",
        "owner_session_key",
        "criado_em",
        "atualizado_em",
    )

    actions = [
        "pausar_perfis",
        "reativar_perfis",
        "bloquear_perfis",
    ]

    def pausar_perfis(self, request, queryset):
        atualizados = queryset.exclude(status="BLOQUEADO").update(
            status="PAUSADO",
            visivel=False
        )

        self.message_user(
            request,
            f"{atualizados} perfil/perfis pausado(s) com sucesso."
        )

    pausar_perfis.short_description = "Pausar perfis selecionados"

    def reativar_perfis(self, request, queryset):
        atualizados = queryset.exclude(status="BLOQUEADO").update(
            status="ATIVO",
            visivel=True
        )

        self.message_user(
            request,
            f"{atualizados} perfil/perfis reativado(s) com sucesso."
        )

    reativar_perfis.short_description = "Reativar perfis selecionados"

    def bloquear_perfis(self, request, queryset):
        atualizados = queryset.update(
            status="BLOQUEADO",
            visivel=False
        )

        self.message_user(
            request,
            f"{atualizados} perfil/perfis bloqueado(s) com sucesso."
        )

    bloquear_perfis.short_description = "Bloquear perfis selecionados"


@admin.register(AcaoPerfil)
class AcaoPerfilAdmin(admin.ModelAdmin):
    list_display = (
        "perfil",
        "tipo",
        "session_key",
        "criado_em",
    )

    list_filter = (
        "tipo",
        "criado_em",
    )

    search_fields = (
        "perfil__nome_publico",
        "session_key",
    )

    readonly_fields = (
        "criado_em",
    )


@admin.register(MensagemPerfil)
class MensagemPerfilAdmin(admin.ModelAdmin):
    list_display = (
        "perfil",
        "tipo",
        "session_key",
        "criado_em",
    )

    list_filter = (
        "tipo",
        "criado_em",
    )

    search_fields = (
        "perfil__nome_publico",
        "session_key",
    )

    readonly_fields = (
        "criado_em",
    )


@admin.register(DenunciaPerfil)
class DenunciaPerfilAdmin(admin.ModelAdmin):
    list_display = (
        "perfil",
        "denunciante",
        "motivo",
        "analisada",
        "perfil_status",
        "perfil_visivel",
        "criado_em",
    )

    list_filter = (
        "motivo",
        "analisada",
        "criado_em",
        "perfil__status",
        "perfil__visivel",
    )

    search_fields = (
        "perfil__nome_publico",
        "perfil__pedido__nome_completo",
        "perfil__pedido__email",
        "denunciante__username",
        "denunciante__email",
        "detalhes",
    )

    readonly_fields = (
        "denunciante",
        "perfil",
        "motivo",
        "detalhes",
        "criado_em",
    )

    actions = [
        "marcar_como_analisada",
        "marcar_como_nao_analisada",
        "pausar_perfis_denunciados",
        "bloquear_perfis_denunciados",
        "reativar_perfis_denunciados",
    ]

    def perfil_status(self, obj):
        return obj.perfil.get_status_display()

    perfil_status.short_description = "Estado do perfil"

    def perfil_visivel(self, obj):
        return "Sim" if obj.perfil.visivel else "Não"

    perfil_visivel.short_description = "Visível"

    def marcar_como_analisada(self, request, queryset):
        atualizadas = queryset.update(analisada=True)

        self.message_user(
            request,
            f"{atualizadas} denúncia(s) marcada(s) como analisada(s)."
        )

    marcar_como_analisada.short_description = "Marcar denúncias como analisadas"

    def marcar_como_nao_analisada(self, request, queryset):
        atualizadas = queryset.update(analisada=False)

        self.message_user(
            request,
            f"{atualizadas} denúncia(s) marcada(s) como não analisada(s)."
        )

    marcar_como_nao_analisada.short_description = "Marcar denúncias como não analisadas"

    def pausar_perfis_denunciados(self, request, queryset):
        perfis_ids = queryset.values_list("perfil_id", flat=True).distinct()

        atualizados = PerfilNKATA.objects.filter(
            id__in=perfis_ids
        ).exclude(
            status="BLOQUEADO"
        ).update(
            status="PAUSADO",
            visivel=False
        )

        queryset.update(analisada=True)

        self.message_user(
            request,
            f"{atualizados} perfil/perfis denunciado(s) pausado(s)."
        )

    pausar_perfis_denunciados.short_description = "Pausar perfis denunciados"

    def bloquear_perfis_denunciados(self, request, queryset):
        perfis_ids = queryset.values_list("perfil_id", flat=True).distinct()

        atualizados = PerfilNKATA.objects.filter(
            id__in=perfis_ids
        ).update(
            status="BLOQUEADO",
            visivel=False
        )

        queryset.update(analisada=True)

        self.message_user(
            request,
            f"{atualizados} perfil/perfis denunciado(s) bloqueado(s)."
        )

    bloquear_perfis_denunciados.short_description = "Bloquear perfis denunciados"

    def reativar_perfis_denunciados(self, request, queryset):
        perfis_ids = queryset.values_list("perfil_id", flat=True).distinct()

        atualizados = PerfilNKATA.objects.filter(
            id__in=perfis_ids
        ).exclude(
            status="BLOQUEADO"
        ).update(
            status="ATIVO",
            visivel=True
        )

        queryset.update(analisada=True)

        self.message_user(
            request,
            f"{atualizados} perfil/perfis denunciado(s) reativado(s)."
        )

    reativar_perfis_denunciados.short_description = "Reativar perfis denunciados"









@admin.register(MatchPerfil)
class MatchPerfilAdmin(admin.ModelAdmin):
    list_display = (
        "perfil_1",
        "perfil_2",
        "tipo_origem",
        "status",
        "criado_em",
    )

    list_filter = (
        "tipo_origem",
        "status",
        "criado_em",
    )

    search_fields = (
        "perfil_1__nome_publico",
        "perfil_2__nome_publico",
        "perfil_1__pedido__email",
        "perfil_2__pedido__email",
    )

    readonly_fields = (
        "perfil_1",
        "perfil_2",
        "tipo_origem",
        "criado_em",
        "atualizado_em",
    )

    actions = [
        "encerrar_matches",
        "reativar_matches",
    ]

    def encerrar_matches(self, request, queryset):
        atualizados = queryset.update(status="ENCERRADO")
        self.message_user(request, f"{atualizados} match(es) encerrado(s).")

    encerrar_matches.short_description = "Encerrar matches selecionados"

    def reativar_matches(self, request, queryset):
        atualizados = queryset.update(status="ATIVO")
        self.message_user(request, f"{atualizados} match(es) reativado(s).")

    reativar_matches.short_description = "Reativar matches selecionados"







@admin.register(MensagemMatch)
class MensagemMatchAdmin(admin.ModelAdmin):
    list_display = (
        "match",
        "remetente",
        "lida",
        "criado_em",
    )

    list_filter = (
        "lida",
        "criado_em",
    )

    search_fields = (
        "texto",
        "remetente__username",
        "remetente__email",
        "match__perfil_1__nome_publico",
        "match__perfil_2__nome_publico",
    )

    readonly_fields = (
        "match",
        "remetente",
        "texto",
        "criado_em",
    )

    actions = ["marcar_como_lida", "marcar_como_nao_lida"]

    def marcar_como_lida(self, request, queryset):
        atualizadas = queryset.update(lida=True)
        self.message_user(request, f"{atualizadas} mensagem(ns) marcada(s) como lida(s).")

    marcar_como_lida.short_description = "Marcar mensagens como lidas"

    def marcar_como_nao_lida(self, request, queryset):
        atualizadas = queryset.update(lida=False)
        self.message_user(request, f"{atualizadas} mensagem(ns) marcada(s) como não lida(s).")

    marcar_como_nao_lida.short_description = "Marcar mensagens como não lidas"