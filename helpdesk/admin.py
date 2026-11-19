from django.contrib import admin
from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "category", "email", "status", "created_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("subject", "email", "description")
    readonly_fields = ("id", "user", "email", "category", "subject", "description", "created_at", "updated_at")
    fields = ("id", "user", "email", "category", "subject", "description", "status", "internal_note", "created_at", "updated_at")
    list_select_related = ("user",)


class SupportReplyInline(admin.TabularInline):
    from .models import SupportReply
    model = SupportReply
    extra = 0
    can_delete = False
    readonly_fields = ("staff", "body", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


SupportTicketAdmin.inlines = [SupportReplyInline]
