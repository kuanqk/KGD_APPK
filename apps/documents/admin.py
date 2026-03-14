from django.contrib import admin
from .models import DocumentTemplate, CaseDocument


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "name", "version", "is_active", "created_by", "created_at")
    list_filter = ("doc_type", "is_active")
    search_fields = ("name", "doc_type")
    ordering = ("doc_type", "-version")
    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CaseDocument)
class CaseDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "doc_number", "doc_type", "case", "version",
        "status", "created_by", "created_at",
    )
    list_filter = ("doc_type", "status", "created_at")
    search_fields = ("doc_number", "case__case_number")
    ordering = ("-created_at",)
    readonly_fields = ("doc_number", "version", "file_path", "metadata", "created_at")
    raw_id_fields = ("case", "template", "created_by")

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == "signed":
            return False
        return super().has_delete_permission(request, obj)
