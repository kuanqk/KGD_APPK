from django.urls import path
from .views import FeedbackCreateView, FeedbackListView, FeedbackMarkReviewedView

app_name = "feedback"

urlpatterns = [
    path("create/", FeedbackCreateView.as_view(), name="create"),
    path("", FeedbackListView.as_view(), name="list"),
    path("<int:pk>/reviewed/", FeedbackMarkReviewedView.as_view(), name="mark_reviewed"),
]
