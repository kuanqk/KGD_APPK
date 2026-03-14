from django.urls import path
from .views import ApprovalQueueView, ApprovalActionView

app_name = "approvals"

urlpatterns = [
    path("", ApprovalQueueView.as_view(), name="queue"),
    path("<int:pk>/action/", ApprovalActionView.as_view(), name="action"),
]
