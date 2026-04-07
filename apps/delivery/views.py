import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, ListView, UpdateView

from apps.cases.models import AdministrativeCase
from apps.documents.models import CaseDocument
from .forms import DeliveryCreateForm, DeliveryFilterForm, DeliveryResultForm
from .models import DeliveryRecord, DeliveryStatus
from .services import create_delivery, mark_delivered, mark_returned

logger = logging.getLogger(__name__)


class DeliveryCreateView(LoginRequiredMixin, FormView):
    template_name = "delivery/create.html"
    form_class = DeliveryCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator", "reviewer"):
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
            sent_at=data.get("sent_at"),
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
        if request.user.role not in ("admin", "operator", "reviewer"):
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


class DeliveryUpdateInlineView(LoginRequiredMixin, View):
    """AJAX endpoint для инлайн-обновления статуса вручения прямо из карточки дела."""

    def post(self, request, pk):
        if request.user.role not in ("admin", "operator", "reviewer"):
            return JsonResponse({"error": "Нет прав."}, status=403)

        delivery = get_object_or_404(
            DeliveryRecord.objects.for_user(request.user).select_related(
                "case_document", "case_document__case"
            ),
            pk=pk,
        )

        action = request.POST.get("result_status") or request.POST.get("action")

        if action == "delivered":
            if delivery.status != DeliveryStatus.PENDING:
                return JsonResponse({"error": "Статус уже зафиксирован."}, status=400)
            delivered_at_str = request.POST.get("delivered_at")
            notes = request.POST.get("notes", "")
            if delivered_at_str:
                from django.utils.dateparse import parse_datetime, parse_date
                dt = parse_datetime(delivered_at_str) or (
                    parse_date(delivered_at_str) and
                    timezone.datetime.combine(parse_date(delivered_at_str), timezone.datetime.min.time())
                )
                if dt:
                    import datetime
                    delivery.delivered_at = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                else:
                    delivery.delivered_at = timezone.now()
            else:
                delivery.delivered_at = timezone.now()
            delivery.status = DeliveryStatus.DELIVERED
            delivery.result = "Вручено"
            if notes:
                delivery.notes = notes
            update_fields = ["status", "delivered_at", "result"]
            if notes:
                update_fields.append("notes")

            # Handle proof_file upload
            if request.FILES.get("proof_file"):
                delivery.proof_file = request.FILES["proof_file"]
                update_fields.append("proof_file")

            delivery.save(update_fields=update_fields)

            # Case event + status
            from apps.cases.models import CaseEvent, CaseEventType, CaseStatus
            from apps.cases.services import change_case_status
            case = delivery.case
            CaseEvent.objects.create(
                case=case,
                event_type=CaseEventType.STATUS_CHANGED,
                description=(
                    f"Документ {delivery.case_document.doc_number} вручён НП"
                    f" ({delivery.get_method_display()})"
                    + (f". {notes}" if notes else "")
                ),
                created_by=request.user,
            )
            if case.status not in (
                CaseStatus.DELIVERED, CaseStatus.HEARING_SCHEDULED,
                CaseStatus.HEARING_DONE, CaseStatus.TERMINATED,
                CaseStatus.COMPLETED, CaseStatus.ARCHIVED,
            ):
                change_case_status(case, CaseStatus.DELIVERED, request.user)

            return JsonResponse({
                "ok": True,
                "status": delivery.status,
                "status_display": delivery.get_status_display(),
                "delivered_at": delivery.delivered_at.strftime("%d.%m.%Y") if delivery.delivered_at else "",
            })

        elif action == "returned":
            if delivery.status != DeliveryStatus.PENDING:
                return JsonResponse({"error": "Статус уже зафиксирован."}, status=400)
            returned_at_str = request.POST.get("returned_at")
            notes = request.POST.get("notes", "")
            if returned_at_str:
                from django.utils.dateparse import parse_datetime, parse_date
                dt = parse_datetime(returned_at_str) or (
                    parse_date(returned_at_str) and
                    timezone.datetime.combine(parse_date(returned_at_str), timezone.datetime.min.time())
                )
                if dt:
                    delivery.returned_at = timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                else:
                    delivery.returned_at = timezone.now()
            else:
                delivery.returned_at = timezone.now()
            delivery.status = DeliveryStatus.RETURNED
            delivery.result = "Возвращено"
            if notes:
                delivery.notes = notes
            update_fields = ["status", "returned_at", "result"]
            if notes:
                update_fields.append("notes")

            if request.FILES.get("proof_file"):
                delivery.proof_file = request.FILES["proof_file"]
                update_fields.append("proof_file")

            delivery.save(update_fields=update_fields)

            from apps.cases.models import CaseEvent, CaseEventType, CaseStatus
            from apps.cases.services import change_case_status
            case = delivery.case
            CaseEvent.objects.create(
                case=case,
                event_type=CaseEventType.STATUS_CHANGED,
                description=(
                    f"Почтовое отправление с документом {delivery.case_document.doc_number} возвращено"
                    + (f". {notes}" if notes else "")
                ),
                created_by=request.user,
            )
            if case.status not in (
                CaseStatus.TERMINATED, CaseStatus.COMPLETED, CaseStatus.ARCHIVED
            ):
                change_case_status(case, CaseStatus.MAIL_RETURNED, request.user)

            return JsonResponse({
                "ok": True,
                "status": delivery.status,
                "status_display": delivery.get_status_display(),
                "returned_at": delivery.returned_at.strftime("%d.%m.%Y") if delivery.returned_at else "",
            })

        # No result_status — save delivered_at and/or proof_file without changing status
        if not action:
            update_fields = []
            delivered_at_str = request.POST.get("delivered_at")
            if delivered_at_str:
                from django.utils.dateparse import parse_date
                dt = parse_date(delivered_at_str)
                if dt:
                    import datetime
                    naive = datetime.datetime.combine(dt, datetime.time.min)
                    delivery.delivered_at = timezone.make_aware(naive)
                    update_fields.append("delivered_at")
            if request.FILES.get("proof_file"):
                delivery.proof_file = request.FILES["proof_file"]
                update_fields.append("proof_file")
            if update_fields:
                delivery.save(update_fields=update_fields)
            return JsonResponse({"ok": True})

        return JsonResponse({"error": "Неизвестное действие."}, status=400)
