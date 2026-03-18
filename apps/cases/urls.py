from django.urls import path
from .views import (
    CaseListView, CaseDetailView, CaseCreateView,
    AllowBackdatingView, TaxpayerImportView, taxpayer_import_template,
    ValidateIinView, ValidatePhoneView,
    ReferenceIndexView,
    RegionListView, RegionCreateView, RegionUpdateView, RegionToggleView, RegionImportView,
    BasisListView, BasisCreateView, BasisUpdateView, BasisToggleView, BasisImportView,
    CategoryListView, CategoryCreateView, CategoryUpdateView, CategoryToggleView, CategoryImportView,
    PositionListView, PositionCreateView, PositionUpdateView, PositionToggleView, PositionImportView,
    DepartmentListView, DepartmentCreateView, DepartmentUpdateView,
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

    # Справочники
    path("references/", ReferenceIndexView.as_view(), name="references"),
    path("references/regions/", RegionListView.as_view(), name="region_list"),
    path("references/regions/create/", RegionCreateView.as_view(), name="region_create"),
    path("references/regions/<int:pk>/edit/", RegionUpdateView.as_view(), name="region_update"),
    path("references/regions/<int:pk>/toggle/", RegionToggleView.as_view(), name="region_toggle"),
    path("references/regions/import/", RegionImportView.as_view(), name="region_import"),

    path("references/basis/", BasisListView.as_view(), name="basis_list"),
    path("references/basis/create/", BasisCreateView.as_view(), name="basis_create"),
    path("references/basis/<int:pk>/edit/", BasisUpdateView.as_view(), name="basis_update"),
    path("references/basis/<int:pk>/toggle/", BasisToggleView.as_view(), name="basis_toggle"),
    path("references/basis/import/", BasisImportView.as_view(), name="basis_import"),

    path("references/categories/", CategoryListView.as_view(), name="category_list"),
    path("references/categories/create/", CategoryCreateView.as_view(), name="category_create"),
    path("references/categories/<int:pk>/edit/", CategoryUpdateView.as_view(), name="category_update"),
    path("references/categories/<int:pk>/toggle/", CategoryToggleView.as_view(), name="category_toggle"),
    path("references/categories/import/", CategoryImportView.as_view(), name="category_import"),

    path("references/positions/", PositionListView.as_view(), name="position_list"),
    path("references/positions/create/", PositionCreateView.as_view(), name="position_create"),
    path("references/positions/<int:pk>/edit/", PositionUpdateView.as_view(), name="position_update"),
    path("references/positions/<int:pk>/toggle/", PositionToggleView.as_view(), name="position_toggle"),
    path("references/positions/import/", PositionImportView.as_view(), name="position_import"),

    path("references/departments/", DepartmentListView.as_view(), name="department_list"),
    path("references/departments/create/", DepartmentCreateView.as_view(), name="department_create"),
    path("references/departments/<int:pk>/edit/", DepartmentUpdateView.as_view(), name="department_update"),
]
