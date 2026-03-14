from django.urls import path
from .views import AuditLogListView, AuditLogExportView

app_name = "audit"

urlpatterns = [
    path("", AuditLogListView.as_view(), name="list"),
    path("export/", AuditLogExportView.as_view(), name="export"),
]
