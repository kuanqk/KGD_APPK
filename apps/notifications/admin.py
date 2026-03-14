from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user", "notification_type", "is_read", "email_sent", "case", "created_at",
    )
    list_filter = ("notification_type", "is_read", "email_sent", "created_at")
    search_fields = ("user__username", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "case")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
