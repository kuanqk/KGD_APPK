from django.urls import path
from .views import (
    CaseListView, CaseDetailView, CaseCreateView,
    AllowBackdatingView, TaxpayerImportView, taxpayer_import_template,
    ValidateIinView, ValidatePhoneView,
)

app_name = "cases"

urlpatterns = [
    path("", CaseListView.as_view(), name="list"),
    path("<int:pk>/", CaseDetailView.as_view(), name="detail"),
    path("create/", CaseCreateView.as_view(), name="create"),
    path("<int:pk>/allow-backdating/", AllowBackdatingView.as_view(), name="allow_backdating"),
    path("taxpayers/import/", TaxpayerImportView.as_view(), name="taxpayer_import"),
    path("taxpayers/import/template/", taxpayer_import_template, name="taxpayer_import_template"),
    path("validate-iin/", ValidateIinView.as_view(), name="validate_iin"),
    path("validate-phone/", ValidatePhoneView.as_view(), name="validate_phone"),
]
