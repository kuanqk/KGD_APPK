from django.contrib import admin
from .models import Department, StagnationSettings, Taxpayer, AdministrativeCase, CaseEvent


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "doc_sequence", "seq_year"]
    search_fields = ["name", "code"]


@admin.register(StagnationSettings)
class StagnationSettingsAdmin(admin.ModelAdmin):
    list_display = ["stagnation_days", "notify_reviewer"]

    def has_add_permission(self, request):
        return not StagnationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Taxpayer)
class TaxpayerAdmin(admin.ModelAdmin):
    list_display = ("iin_bin", "name", "taxpayer_type", "phone", "email", "created_at")
    list_filter = ("taxpayer_type",)
    search_fields = ("iin_bin", "name", "email")
    ordering = ("name",)


@admin.register(AdministrativeCase)
class AdministrativeCaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_number", "status", "taxpayer", "region",
        "responsible_user", "created_by", "created_at",
    )
    list_filter = ("status", "basis", "region", "created_at")
    search_fields = ("case_number", "taxpayer__iin_bin", "taxpayer__name")
    ordering = ("-created_at",)
    raw_id_fields = ("taxpayer", "responsible_user", "created_by")
    readonly_fields = ("case_number", "created_at", "updated_at")


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ("case", "event_type", "created_by", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("case__case_number", "description")
    ordering = ("-created_at",)
    raw_id_fields = ("case", "created_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
