from django.contrib import admin
from .models import Feedback


@admin.action(description="Отметить как рассмотренные")
def mark_reviewed(modeladmin, request, queryset):
    queryset.update(is_reviewed=True)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "feedback_type", "case_number", "is_reviewed"]
    list_filter = ["feedback_type", "is_reviewed", "created_at"]
    search_fields = ["description", "case_number", "user__username", "user__last_name"]
    readonly_fields = ["user", "feedback_type", "description", "case_number", "attachment", "created_at"]
    actions = [mark_reviewed]
