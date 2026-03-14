from django.contrib import admin
from .models import FinalDecision


@admin.register(FinalDecision)
class FinalDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "case", "decision_type", "status", "basis",
        "created_by", "approver", "approved_at", "created_at",
    )
    list_filter = ("decision_type", "status", "created_at")
    search_fields = ("case__case_number", "case__taxpayer__name")
    ordering = ("-created_at",)
    raw_id_fields = ("case", "responsible", "approver", "created_by")
    readonly_fields = ("decision_date", "created_at", "approved_at")

    def has_delete_permission(self, request, obj=None):
        # Нельзя удалять утверждённые решения
        if obj and obj.status == "approved":
            return False
        return super().has_delete_permission(request, obj)
