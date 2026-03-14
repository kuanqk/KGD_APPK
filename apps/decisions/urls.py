from django.urls import path
from .views import (
    DecisionListView,
    TerminationCreateView, TaxAuditCreateView,
    DecisionDetailView, DecisionApproveView,
)

app_name = "decisions"

urlpatterns = [
    path("", DecisionListView.as_view(), name="list"),
    path("cases/<int:case_pk>/terminate/", TerminationCreateView.as_view(), name="terminate"),
    path("cases/<int:case_pk>/tax-audit/", TaxAuditCreateView.as_view(), name="tax_audit"),
    path("<int:pk>/", DecisionDetailView.as_view(), name="detail"),
    path("<int:pk>/review/", DecisionApproveView.as_view(), name="review"),
]
