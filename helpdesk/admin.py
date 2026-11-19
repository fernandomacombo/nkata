from django.contrib import admin
from .models import SupportTicket, SupportReply


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "category", "email", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("subject", "email", "description")
    readonly_fields = ("id", "user", "email", "category", "subject", "description", "created_at", "updated_at")
    fields = ("id", "user", "email", "category", "subject", "description", "status", "internal_note", "created_at", "updated_at")
    list_select_related = ("user",)

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


class SupportReplyInline(admin.TabularInline):
    model = SupportReply
    extra = 0
    can_delete = False
    readonly_fields = ("staff", "body", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


SupportTicketAdmin.inlines = [SupportReplyInline]
