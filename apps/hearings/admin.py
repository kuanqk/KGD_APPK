from django.contrib import admin
from .models import Hearing, HearingProtocol


@admin.register(Hearing)
class HearingAdmin(admin.ModelAdmin):
    list_display = ("case", "hearing_date", "hearing_time", "format", "status", "created_by")
    list_filter = ("status", "format", "hearing_date")
    search_fields = ("case__case_number", "location")
    ordering = ("-hearing_date",)
    raw_id_fields = ("case", "created_by")
    readonly_fields = ("created_at",)


@admin.register(HearingProtocol)
class HearingProtocolAdmin(admin.ModelAdmin):
    list_display = (
        "protocol_number", "case", "hearing", "protocol_date",
        "deadline_2days", "is_deadline_overdue", "created_by",
    )
    list_filter = ("protocol_date", "deadline_2days")
    search_fields = ("protocol_number", "case__case_number")
    ordering = ("-protocol_date",)
    raw_id_fields = ("case", "hearing", "created_by")
    readonly_fields = ("protocol_number", "deadline_2days", "created_at")

    @admin.display(boolean=True, description="Просрочен")
    def is_deadline_overdue(self, obj):
        return obj.is_deadline_overdue
