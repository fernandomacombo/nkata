from django.contrib import admin
from .models import PedidoPagamentoNKATA


@admin.register(PedidoPagamentoNKATA)
class PedidoPagamentoAdmin(admin.ModelAdmin):
    list_display = ("referencia", "usuario", "produto", "valor", "estado", "confirmado_em", "aplicado_em")
    list_filter = ("estado", "produto")
    search_fields = ("referencia", "provedor_id", "usuario__email")
    readonly_fields = tuple(field.name for field in PedidoPagamentoNKATA._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
