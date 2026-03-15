from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls", namespace="accounts")),
    path("cases/", include("apps.cases.urls", namespace="cases")),
    path("documents/", include("apps.documents.urls", namespace="documents")),
    path("delivery/", include("apps.delivery.urls", namespace="delivery")),
    path("hearings/", include("apps.hearings.urls", namespace="hearings")),
    path("decisions/", include("apps.decisions.urls", namespace="decisions")),
    path("approvals/", include("apps.approvals.urls", namespace="approvals")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("audit/", include("apps.audit.urls", namespace="audit")),
    path("feedback/", include("apps.feedback.urls", namespace="feedback")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
