from django.urls import path
from .views import DocumentCreateView, DocumentDetailView, document_download

app_name = "documents"

urlpatterns = [
    path("cases/<int:case_pk>/documents/create/", DocumentCreateView.as_view(), name="create"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="detail"),
    path("<int:pk>/download/", document_download, name="download"),
]
