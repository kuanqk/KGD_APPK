from django.contrib import admin
from .models import DeliveryRecord


@admin.register(DeliveryRecord)
class DeliveryRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id", "case_document", "method", "status",
        "tracking_number", "sent_at", "delivered_at", "returned_at", "created_by",
    )
    list_filter = ("method", "status", "created_at")
    search_fields = (
        "tracking_number",
        "case_document__doc_number",
        "case_document__case__case_number",
    )
    ordering = ("-created_at",)
    raw_id_fields = ("case_document", "created_by")
    readonly_fields = ("sent_at", "delivered_at", "returned_at", "created_at")

    def has_delete_permission(self, request, obj=None):
        return False
