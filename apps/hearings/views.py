import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView, ListView

from apps.cases.models import AdministrativeCase, CaseStatus
from .forms import HearingScheduleForm, ProtocolCreateForm
from .models import Hearing, HearingProtocol, HearingStatus
from .services import HEARING_ALLOWED_STATUSES, complete_hearing, create_protocol, schedule_hearing

logger = logging.getLogger(__name__)


class HearingScheduleView(LoginRequiredMixin, FormView):
    template_name = "hearings/schedule.html"
    form_class = HearingScheduleForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для назначения заслушиваний.")
            return redirect("cases:list")

        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )

        if self.case.status not in HEARING_ALLOWED_STATUSES:
            messages.error(
                request,
                f"Нельзя назначить заслушивание при статусе «{self.case.get_status_display()}»."
            )
            return redirect("cases:detail", pk=self.case.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        hearing = schedule_hearing(
            case=self.case,
            hearing_date=data["hearing_date"],
            location=data["location"],
            user=self.request.user,
            hearing_time=data.get("hearing_time"),
            format=data["format"],
            participants=data.get("participants", []),
            notes=data.get("notes", ""),
        )
        messages.success(
            self.request,
            f"Заслушивание назначено на {hearing.hearing_date:%d.%m.%Y}."
        )
        return redirect("hearings:detail", pk=hearing.pk)


class HearingDetailView(LoginRequiredMixin, DetailView):
    template_name = "hearings/detail.html"
    context_object_name = "hearing"

    def get_queryset(self):
        return (
            Hearing.objects
            .for_user(self.request.user)
            .select_related("case", "case__taxpayer", "created_by")
            .prefetch_related("protocol")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_complete"] = (
            self.object.status == HearingStatus.SCHEDULED
            and self.request.user.role in ("admin", "operator")
        )
        context["can_create_protocol"] = (
            self.object.status == HearingStatus.COMPLETED
            and not self.object.has_protocol
            and self.request.user.role in ("admin", "operator")
        )
        try:
            context["protocol"] = self.object.protocol
        except HearingProtocol.DoesNotExist:
            context["protocol"] = None

        # Явно ищем CaseDocument протокола чтобы шаблон получил валидный pk
        from apps.documents.models import DocumentType, CaseDocument
        context["protocol_doc"] = (
            CaseDocument.objects
            .filter(
                case=self.object.case,
                doc_type=DocumentType.HEARING_PROTOCOL,
            )
            .order_by("-created_at")
            .first()
        )
        return context


class HearingCompleteView(LoginRequiredMixin, FormView):
    """Подтверждение факта проведения заслушивания."""
    template_name = "hearings/complete.html"
    form_class = ProtocolCreateForm  # пустая форма — просто подтверждение

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав.")
            return redirect("cases:list")

        self.hearing = get_object_or_404(
            Hearing.objects.for_user(request.user),
            pk=kwargs["pk"],
        )

        if self.hearing.status != HearingStatus.SCHEDULED:
            messages.warning(request, "Заслушивание уже завершено или отменено.")
            return redirect("hearings:detail", pk=self.hearing.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        from django import forms

        class ConfirmForm(forms.Form):
            pass

        return ConfirmForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hearing"] = self.hearing
        return context

    def form_valid(self, form):
        complete_hearing(self.hearing, self.request.user)
        messages.success(self.request, "Заслушивание зафиксировано как проведённое.")
        return redirect("hearings:detail", pk=self.hearing.pk)


class ProtocolCreateView(LoginRequiredMixin, FormView):
    template_name = "hearings/protocol_create.html"
    form_class = ProtocolCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для оформления протокола.")
            return redirect("cases:list")

        self.hearing = get_object_or_404(
            Hearing.objects.for_user(request.user),
            pk=kwargs["pk"],
        )

        if self.hearing.status != HearingStatus.COMPLETED:
            messages.error(request, "Протокол оформляется только после проведения заслушивания.")
            return redirect("hearings:detail", pk=self.hearing.pk)

        if self.hearing.has_protocol:
            messages.warning(request, "Протокол уже оформлен.")
            return redirect("hearings:detail", pk=self.hearing.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["hearing"] = self.hearing
        return context

    def form_valid(self, form):
        try:
            protocol = create_protocol(
                hearing=self.hearing,
                result_summary=form.cleaned_data["result_summary"],
                user=self.request.user,
            )
            messages.success(
                self.request,
                f"Протокол {protocol.protocol_number} оформлен. "
                f"Дедлайн решения: {protocol.deadline_2days:%d.%m.%Y}."
            )
            return redirect("hearings:detail", pk=self.hearing.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class CalendarView(LoginRequiredMixin, ListView):
    template_name = "hearings/calendar.html"
    context_object_name = "hearings"

    def get_queryset(self):
        return (
            Hearing.objects
            .for_user(self.request.user)
            .select_related("case", "case__taxpayer")
            .order_by("hearing_date", "hearing_time")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["upcoming"] = [h for h in context["hearings"] if h.status == HearingStatus.SCHEDULED]
        context["past"] = [h for h in context["hearings"] if h.status != HearingStatus.SCHEDULED]
        return context
