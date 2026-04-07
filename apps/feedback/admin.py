from django.contrib import admin
from django.utils import timezone
from .models import Feedback, FeedbackStatus


@admin.action(description="Отметить как рассмотренные (Исправлено)")
def mark_resolved(modeladmin, request, queryset):
    queryset.update(status=FeedbackStatus.RESOLVED, is_reviewed=True, resolved_at=timezone.now())


@admin.action(description="Взять в работу")
def mark_in_progress(modeladmin, request, queryset):
    queryset.update(status=FeedbackStatus.IN_PROGRESS)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "created_at", "user", "feedback_type", "status", "priority",
        "case_number", "is_reviewed",
    ]
    list_filter = ["feedback_type", "status", "priority", "is_reviewed", "created_at"]
    list_editable = ["status", "priority"]
    search_fields = ["description", "case_number", "user__username", "user__last_name"]
    readonly_fields = [
        "user", "feedback_type", "description", "case_number",
        "attachment", "created_at", "resolved_at",
    ]
    fields = [
        "user", "feedback_type", "status", "priority",
        "description", "case_number", "attachment",
        "admin_comment", "created_at", "resolved_at", "is_reviewed",
    ]
    actions = [mark_resolved, mark_in_progress]
