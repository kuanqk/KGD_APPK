import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView

from apps.cases.models import AdministrativeCase, CaseStatus
from .forms import DecisionReviewForm, TerminationCreateForm, TaxAuditCreateForm
from .models import FinalDecision, DecisionStatus
from .services import approve_decision, create_tax_audit, create_termination, reject_decision

logger = logging.getLogger(__name__)


class DecisionListView(LoginRequiredMixin, ListView):
    template_name = "decisions/list.html"
    context_object_name = "decisions"
    paginate_by = 20

    def get_queryset(self):
        qs = FinalDecision.objects.for_user(self.request.user).select_related(
            "case", "case__taxpayer", "created_by", "approver"
        )
        # Reviewer/admin sees pending-only by default unless filtered
        status_filter = self.request.GET.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        elif self.request.user.role in ("admin", "reviewer"):
            qs = qs.filter(status=DecisionStatus.PENDING_APPROVAL)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["DecisionStatus"] = DecisionStatus
        return context


class TerminationCreateView(LoginRequiredMixin, FormView):
    template_name = "decisions/termination_create.html"
    form_class = TerminationCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания решений.")
            return redirect("cases:list")

        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )

        if self.case.status != CaseStatus.PROTOCOL_CREATED:
            messages.error(
                request,
                f"Прекращение недоступно при статусе «{self.case.get_status_display()}». "
                f"Требуется оформленный протокол заслушивания."
            )
            return redirect("cases:detail", pk=self.case.pk)

        if hasattr(self.case, "final_decision"):
            messages.warning(request, "По данному делу уже создано итоговое решение.")
            return redirect("decisions:detail", pk=self.case.final_decision.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        return context

    def form_valid(self, form):
        try:
            decision = create_termination(
                case=self.case,
                basis=form.cleaned_data["basis"],
                comment=form.cleaned_data["comment"],
                user=self.request.user,
            )
            messages.success(
                self.request,
                "Решение о прекращении составлено и направлено на согласование."
            )
            return redirect("decisions:detail", pk=decision.pk)
        except (PermissionDenied, ValueError) as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class TaxAuditCreateView(LoginRequiredMixin, FormView):
    template_name = "decisions/tax_audit_create.html"
    form_class = TaxAuditCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания решений.")
            return redirect("cases:list")

        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )

        if self.case.status != CaseStatus.PROTOCOL_CREATED:
            messages.error(
                request,
                f"Назначение проверки недоступно при статусе «{self.case.get_status_display()}»."
            )
            return redirect("cases:detail", pk=self.case.pk)

        if hasattr(self.case, "final_decision"):
            messages.warning(request, "По данному делу уже создано итоговое решение.")
            return redirect("decisions:detail", pk=self.case.final_decision.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        return context

    def form_valid(self, form):
        try:
            decision = create_tax_audit(
                case=self.case,
                comment=form.cleaned_data["comment"],
                user=self.request.user,
            )
            messages.success(
                self.request,
                "Инициирование проверки оформлено и направлено на согласование."
            )
            return redirect("decisions:detail", pk=decision.pk)
        except (PermissionDenied, ValueError) as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class DecisionDetailView(LoginRequiredMixin, DetailView):
    template_name = "decisions/detail.html"
    context_object_name = "decision"

    def get_queryset(self):
        return FinalDecision.objects.for_user(self.request.user).select_related(
            "case", "case__taxpayer", "created_by", "approver", "responsible"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_review"] = (
            self.object.status == DecisionStatus.PENDING_APPROVAL
            and self.request.user.role in ("admin", "reviewer")
        )
        context["can_archive"] = (
            self.object.status == DecisionStatus.APPROVED
            and self.object.case.status in ("terminated", "audit_approved", "completed")
            and self.request.user.role in ("admin", "operator")
        )
        return context

    def post(self, request, *args, **kwargs):
        decision = self.get_object()
        action = request.POST.get("action")

        if action == "archive" and decision.case.status in ("terminated", "audit_approved", "completed"):
            from .services import archive_case
            try:
                archive_case(decision.case, request.user)
                messages.success(request, "Дело переведено в архив.")
            except ValueError as e:
                messages.error(request, str(e))

        return redirect("decisions:detail", pk=decision.pk)


class DecisionApproveView(LoginRequiredMixin, FormView):
    template_name = "decisions/approve.html"
    form_class = DecisionReviewForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "reviewer"):
            messages.error(request, "Согласование доступно только руководителю.")
            return redirect("cases:list")

        self.decision = get_object_or_404(
            FinalDecision.objects.for_user(request.user).select_related(
                "case", "case__taxpayer", "created_by"
            ),
            pk=kwargs["pk"],
        )

        if self.decision.status != DecisionStatus.PENDING_APPROVAL:
            messages.warning(request, "Решение уже рассмотрено.")
            return redirect("decisions:detail", pk=self.decision.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["decision"] = self.decision
        return context

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        try:
            if action == "approve":
                approve_decision(self.decision, self.request.user)
                messages.success(self.request, "Решение утверждено.")
            else:
                reject_decision(
                    self.decision,
                    self.request.user,
                    form.cleaned_data["rejection_comment"],
                )
                messages.warning(self.request, "Решение отклонено. Дело возвращено на доработку.")
            return redirect("decisions:detail", pk=self.decision.pk)
        except (PermissionDenied, ValueError) as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
