from django.contrib import admin
from django.utils.html import format_html


def _badge(texto, fundo, cor):
    return format_html(
        '<span style="display:inline-block;padding:5px 9px;border-radius:999px;'
        'background:{};color:{};font-size:11px;font-weight:700;white-space:nowrap;">{}</span>',
        fundo,
        cor,
        texto,
    )


def aplicar_fluxo_de_aprovacao_admin():
    from .admin import PedidoEntradaAdmin

    def get_queryset(self, request):
        return (
            super(PedidoEntradaAdmin, self)
            .get_queryset(request)
            .select_related("perfil__usuario", "questionario")
        )

    def progresso_acesso(self, obj):
        if obj.status == "BLOQUEADO":
            return _badge("Bloqueado", "#f9e1e5", "#8d2336")

        if obj.status != "APROVADO":
            return _badge(obj.get_status_display(), "#f2eee8", "#625a55")

        questionario = getattr(obj, "questionario", None)
        if not questionario:
            return _badge("Aguardando questionário", "#fff2d8", "#8a5b16")

        perfil = getattr(obj, "perfil", None)
        if not perfil:
            return _badge("A preparar perfil", "#e8eef8", "#34547d")

        usuario = perfil.usuario
        if not usuario or not usuario.has_usable_password():
            return _badge("Aguardando palavra-passe", "#f3e8f7", "#6e3b78")

        if perfil.status == "ATIVO" and perfil.visivel:
            return _badge("Conta ativa", "#e5f2eb", "#2d624c")

        if perfil.status == "BLOQUEADO":
            return _badge("Perfil bloqueado", "#f9e1e5", "#8d2336")

        return _badge("Perfil oculto", "#eee9e4", "#5f5751")

    progresso_acesso.short_description = "Progresso do acesso"
    progresso_acesso.admin_order_field = "status"

    def _alterar_status(self, request, queryset, status, mensagem):
        atualizados = 0
        for pedido in queryset:
            if pedido.status == status:
                continue
            pedido.status = status
            pedido.save(update_fields=["status", "atualizado_em"])
            atualizados += 1

        self.message_user(request, mensagem.format(total=atualizados))

    @admin.action(description="Marcar como em análise")
    def marcar_como_em_analise(self, request, queryset):
        _alterar_status(
            self,
            request,
            queryset,
            "EM_ANALISE",
            "{total} pedido(s) colocado(s) em análise. Perfis associados foram ocultados.",
        )

    @admin.action(description="Aprovar pedidos selecionados")
    def marcar_como_aprovado(self, request, queryset):
        _alterar_status(
            self,
            request,
            queryset,
            "APROVADO",
            "{total} pedido(s) aprovado(s). O questionário fica disponível; a conta só será ativada depois de a pessoa criar a própria palavra-passe.",
        )

    @admin.action(description="Marcar como precisa corrigir")
    def marcar_como_precisa_corrigir(self, request, queryset):
        _alterar_status(
            self,
            request,
            queryset,
            "PRECISA_CORRIGIR",
            "{total} pedido(s) marcado(s) para correção. Perfis associados foram ocultados.",
        )

    @admin.action(description="Recusar pedidos selecionados")
    def marcar_como_recusado(self, request, queryset):
        _alterar_status(
            self,
            request,
            queryset,
            "RECUSADO",
            "{total} pedido(s) recusado(s). Perfis associados foram ocultados.",
        )

    @admin.action(description="Bloquear pedidos selecionados")
    def marcar_como_bloqueado(self, request, queryset):
        _alterar_status(
            self,
            request,
            queryset,
            "BLOQUEADO",
            "{total} pedido(s) bloqueado(s). Perfis e acessos associados foram bloqueados.",
        )

    PedidoEntradaAdmin.get_queryset = get_queryset
    PedidoEntradaAdmin.progresso_acesso = progresso_acesso
    PedidoEntradaAdmin.marcar_como_em_analise = marcar_como_em_analise
    PedidoEntradaAdmin.marcar_como_aprovado = marcar_como_aprovado
    PedidoEntradaAdmin.marcar_como_precisa_corrigir = marcar_como_precisa_corrigir
    PedidoEntradaAdmin.marcar_como_recusado = marcar_como_recusado
    PedidoEntradaAdmin.marcar_como_bloqueado = marcar_como_bloqueado

    colunas = list(PedidoEntradaAdmin.list_display)
    if "progresso_acesso" not in colunas:
        indice = colunas.index("criado_em") if "criado_em" in colunas else len(colunas)
        colunas.insert(indice, "progresso_acesso")
        PedidoEntradaAdmin.list_display = tuple(colunas)
