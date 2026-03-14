from django.urls import path
from .views import ReportDashboardView, ReportDetailView, ExportView

app_name = "reports"

urlpatterns = [
    path("", ReportDashboardView.as_view(), name="dashboard"),
    path("<str:report_type>/", ReportDetailView.as_view(), name="detail"),
    path("<str:report_type>/export/", ExportView.as_view(), name="export"),
]
