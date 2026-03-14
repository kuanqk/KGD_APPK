from django.contrib import admin
from .models import ApprovalFlow


@admin.register(ApprovalFlow)
class ApprovalFlowAdmin(admin.ModelAdmin):
    list_display = (
        "entity_type", "entity_id", "version", "result",
        "sent_by", "sent_at", "reviewed_by", "reviewed_at",
    )
    list_filter = ("entity_type", "result", "sent_at")
    search_fields = ("sent_by__username", "reviewed_by__username", "comment")
    ordering = ("-sent_at",)
    readonly_fields = ("sent_at", "reviewed_at")
    raw_id_fields = ("sent_by", "reviewed_by")

    def has_delete_permission(self, request, obj=None):
        return False
