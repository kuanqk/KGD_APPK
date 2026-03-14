from django.urls import path
from .views import CaseListView, CaseDetailView, CaseCreateView

app_name = "cases"

urlpatterns = [
    path("", CaseListView.as_view(), name="list"),
    path("<int:pk>/", CaseDetailView.as_view(), name="detail"),
    path("create/", CaseCreateView.as_view(), name="create"),
]
