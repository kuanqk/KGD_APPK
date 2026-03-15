import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, FormView

from .forms import CaseCreateForm, CaseFilterForm
from .models import AdministrativeCase
from .services import create_case, allow_backdating

logger = logging.getLogger(__name__)


class CaseListView(LoginRequiredMixin, ListView):
    model = AdministrativeCase
    template_name = "cases/list.html"
    context_object_name = "cases"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            AdministrativeCase.objects
            .for_user(self.request.user)
            .select_related("taxpayer", "responsible_user", "created_by")
        )
        form = CaseFilterForm(self.request.GET)
        if not form.is_valid():
            return qs

        if form.cleaned_data.get("status"):
            qs = qs.filter(status=form.cleaned_data["status"])
        if form.cleaned_data.get("region"):
            qs = qs.filter(region__icontains=form.cleaned_data["region"])
        if form.cleaned_data.get("responsible_user"):
            qs = qs.filter(responsible_user=form.cleaned_data["responsible_user"])
        if form.cleaned_data.get("date_from"):
            qs = qs.filter(created_at__date__gte=form.cleaned_data["date_from"])
        if form.cleaned_data.get("date_to"):
            qs = qs.filter(created_at__date__lte=form.cleaned_data["date_to"])
        if form.cleaned_data.get("search"):
            q = form.cleaned_data["search"]
            qs = qs.filter(
                Q(case_number__icontains=q)
                | Q(taxpayer__iin_bin__icontains=q)
                | Q(taxpayer__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = CaseFilterForm(self.request.GET)
        return context


class CaseDetailView(LoginRequiredMixin, DetailView):
    model = AdministrativeCase
    template_name = "cases/detail.html"
    context_object_name = "case"

    def get_queryset(self):
        return (
            AdministrativeCase.objects
            .for_user(self.request.user)
            .select_related("taxpayer", "responsible_user", "created_by")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["events"] = (
            self.object.events
            .select_related("created_by")
            .order_by("-created_at")[:50]
        )
        # История согласований по итоговому решению дела (если есть)
        if hasattr(self.object, "final_decision"):
            from apps.approvals.services import get_history
            from apps.approvals.models import ApprovalFlow, ApprovalResult
            decision = self.object.final_decision
            context["approval_history"] = get_history(decision)
            context["pending_flow"] = (
                ApprovalFlow.objects
                .filter(entity_type="decision", entity_id=decision.pk, result=ApprovalResult.PENDING)
                .order_by("-version")
                .first()
            )
        return context


class CaseCreateView(LoginRequiredMixin, FormView):
    template_name = "cases/create.html"
    form_class = CaseCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания дел.")
            return redirect("cases:list")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if user.department_id and user.role not in ("admin", "observer"):
            initial["department"] = user.department_id
        return initial

    def form_valid(self, form):
        data = form.cleaned_data
        case = create_case(
            operator=self.request.user,
            taxpayer_data={
                "iin_bin": data["iin_bin"],
                "name": data["taxpayer_name"],
                "taxpayer_type": data["taxpayer_type"],
                "address": data.get("taxpayer_address", ""),
                "phone": data.get("taxpayer_phone", ""),
                "email": data.get("taxpayer_email", ""),
            },
            region=data["region"],
            basis=data["basis"],
            department=data.get("department"),
            category=data.get("category", ""),
            description=data.get("description", ""),
            responsible_user=data.get("responsible_user"),
        )
        messages.success(self.request, f"Дело {case.case_number} успешно создано.")
        return redirect("cases:detail", pk=case.pk)


class AllowBackdatingView(LoginRequiredMixin, View):
    """POST cases/<pk>/allow-backdating/ — разрешить ввод документов задним числом."""

    def post(self, request, pk):
        if request.user.role not in ("admin", "reviewer"):
            raise Http404

        case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=pk,
        )
        comment = request.POST.get("comment", "").strip()

        try:
            allow_backdating(case, request.user, comment)
            messages.success(
                request,
                f"Ввод документов задним числом по делу {case.case_number} разрешён."
            )
        except PermissionDenied as e:
            messages.error(request, str(e))

        return redirect("cases:detail", pk=pk)
