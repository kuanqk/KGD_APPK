from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "region", "is_active", "date_joined")
    list_filter = ("role", "region", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("last_name", "first_name")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("АППК", {
            "fields": ("role", "region", "phone", "position"),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("АППК", {
            "fields": ("role", "region", "phone", "position"),
        }),
    )
