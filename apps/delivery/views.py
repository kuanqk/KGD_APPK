import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, ListView, UpdateView

from apps.cases.models import AdministrativeCase
from apps.documents.models import CaseDocument
from .forms import DeliveryCreateForm, DeliveryFilterForm, DeliveryResultForm
from .models import DeliveryRecord
from .services import create_delivery, mark_delivered, mark_returned

logger = logging.getLogger(__name__)


class DeliveryCreateView(LoginRequiredMixin, FormView):
    template_name = "delivery/create.html"
    form_class = DeliveryCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания записей о доставке.")
            return redirect("cases:list")

        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )
        # Документ можно передать через GET-параметр или выбрать в форме
        doc_id = request.GET.get("document_id") or request.POST.get("document_id")
        if doc_id:
            self.document = get_object_or_404(
                CaseDocument.objects.for_user(request.user),
                pk=doc_id,
                case=self.case,
            )
        else:
            self.document = None

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.document:
            initial["document_id"] = self.document.pk
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        context["document"] = self.document
        context["case_documents"] = (
            CaseDocument.objects
            .filter(case=self.case)
            .exclude(status="cancelled")
            .order_by("-created_at")
        )
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        doc_id = data["document_id"]
        document = get_object_or_404(
            CaseDocument.objects.for_user(self.request.user),
            pk=doc_id,
            case=self.case,
        )
        delivery = create_delivery(
            document=document,
            method=data["method"],
            user=self.request.user,
            tracking_number=data.get("tracking_number", ""),
            notes=data.get("notes", ""),
        )
        messages.success(
            self.request,
            f"Отправка документа {document.doc_number} зафиксирована."
        )
        return redirect("cases:detail", pk=self.case.pk)


class DeliveryUpdateView(LoginRequiredMixin, FormView):
    template_name = "delivery/update.html"
    form_class = DeliveryResultForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для обновления записей о доставке.")
            return redirect("cases:list")

        self.delivery = get_object_or_404(
            DeliveryRecord.objects.for_user(request.user).select_related(
                "case_document", "case_document__case", "case_document__case__taxpayer"
            ),
            pk=kwargs["pk"],
        )

        if self.delivery.status != "pending":
            messages.warning(request, "Результат доставки уже зафиксирован.")
            return redirect("cases:detail", pk=self.delivery.case.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["delivery"] = self.delivery
        context["case"] = self.delivery.case
        return context

    def form_valid(self, form):
        result_status = form.cleaned_data["result_status"]
        notes = form.cleaned_data.get("notes", "")

        if result_status == "delivered":
            mark_delivered(self.delivery, self.request.user, notes=notes)
            messages.success(self.request, "Вручение зафиксировано.")
        else:
            mark_returned(self.delivery, self.request.user, notes=notes)
            messages.warning(self.request, "Возврат почтового отправления зафиксирован.")

        return redirect("cases:detail", pk=self.delivery.case.pk)


class DeliveryListView(LoginRequiredMixin, ListView):
    template_name = "delivery/list.html"
    context_object_name = "deliveries"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            DeliveryRecord.objects
            .for_user(self.request.user)
            .select_related(
                "case_document",
                "case_document__case",
                "case_document__case__taxpayer",
                "created_by",
            )
        )
        form = DeliveryFilterForm(self.request.GET)
        if not form.is_valid():
            return qs

        if form.cleaned_data.get("status"):
            qs = qs.filter(status=form.cleaned_data["status"])
        if form.cleaned_data.get("method"):
            qs = qs.filter(method=form.cleaned_data["method"])
        if form.cleaned_data.get("date_from"):
            qs = qs.filter(created_at__date__gte=form.cleaned_data["date_from"])
        if form.cleaned_data.get("date_to"):
            qs = qs.filter(created_at__date__lte=form.cleaned_data["date_to"])
        if form.cleaned_data.get("search"):
            q = form.cleaned_data["search"]
            qs = qs.filter(
                Q(tracking_number__icontains=q)
                | Q(case_document__doc_number__icontains=q)
                | Q(case_document__case__case_number__icontains=q)
                | Q(case_document__case__taxpayer__name__icontains=q)
                | Q(case_document__case__taxpayer__iin_bin__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = DeliveryFilterForm(self.request.GET)
        return context
