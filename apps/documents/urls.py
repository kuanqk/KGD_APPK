from django.urls import path
from .views import (
    DocumentCreateView, DocumentDetailView, document_download,
    InspectionActCreateView, DerRequestCreateView, NoticeCreateView,
)

app_name = "documents"

urlpatterns = [
    path("cases/<int:case_pk>/documents/create/", DocumentCreateView.as_view(), name="create"),
    path("cases/<int:case_pk>/notice/create/", NoticeCreateView.as_view(), name="notice_create"),
    path("cases/<int:case_pk>/act/create/", InspectionActCreateView.as_view(), name="act_create"),
    path("cases/<int:case_pk>/der/create/", DerRequestCreateView.as_view(), name="der_create"),
    path("<int:pk>/", DocumentDetailView.as_view(), name="detail"),
    path("<int:pk>/download/", document_download, name="download"),
]
