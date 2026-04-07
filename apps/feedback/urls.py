from django.urls import path
from .views import (
    FeedbackCreateView,
    FeedbackDetailView,
    FeedbackExportCsvView,
    FeedbackListView,
    FeedbackMarkReviewedView,
    FeedbackStatsView,
    FeedbackUpdateView,
)

app_name = "feedback"

urlpatterns = [
    path("create/", FeedbackCreateView.as_view(), name="create"),
    path("", FeedbackListView.as_view(), name="list"),
    path("stats/", FeedbackStatsView.as_view(), name="stats"),
    path("export/csv/", FeedbackExportCsvView.as_view(), name="export_csv"),
    path("<int:pk>/", FeedbackDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", FeedbackUpdateView.as_view(), name="update"),
    path("<int:pk>/reviewed/", FeedbackMarkReviewedView.as_view(), name="mark_reviewed"),
]
