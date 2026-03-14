from django.urls import path
from .views import NotificationListView, MarkReadView, MarkAllReadView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("<int:pk>/read/", MarkReadView.as_view(), name="mark_read"),
    path("read-all/", MarkAllReadView.as_view(), name="mark_all_read"),
]
