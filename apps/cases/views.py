import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import Now
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, FormView

from .forms import CaseCreateForm, CaseFilterForm, TaxpayerImportForm
from .models import AdministrativeCase, StagnationSettings, Taxpayer, TaxpayerType
from .services import create_case, allow_backdating
from .validators import KZValidator, IIN_BIN_ERRORS

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
            .annotate(
                days_stagnant=ExpressionWrapper(
                    Now() - F("last_activity_at"),
                    output_field=DurationField(),
                )
            )
        )
        form = CaseFilterForm(self.request.GET)
        if not form.is_valid():
            return qs

        if form.cleaned_data.get("status"):
            qs = qs.filter(status=form.cleaned_data["status"])
        if form.cleaned_data.get("department"):
            qs = qs.filter(department=form.cleaned_data["department"])
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
        context["show_dept_filter"] = self.request.user.role in ("admin", "reviewer")
        threshold = StagnationSettings.get().stagnation_days
        context["stagnation_threshold"] = threshold
        context["stagnation_warn_threshold"] = int(threshold * 0.8)
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


# Маппинг русских обозначений типа НП → внутренние коды
_TAXPAYER_TYPE_MAP = {
    "юл": TaxpayerType.LEGAL,
    "юр": TaxpayerType.LEGAL,
    "фл": TaxpayerType.INDIVIDUAL,
    "физ": TaxpayerType.INDIVIDUAL,
    "ип": TaxpayerType.IE,
}


class TaxpayerImportView(LoginRequiredMixin, View):
    """GET/POST cases/taxpayers/import/ — импорт НП из Excel."""
    template_name = "cases/taxpayer_import.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name, {"form": TaxpayerImportForm()})

    def post(self, request):
        from django.shortcuts import render
        from apps.audit.services import audit_log

        form = TaxpayerImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        uploaded = request.FILES["file"]
        if not uploaded.name.endswith(".xlsx"):
            messages.error(request, "Принимаются только файлы .xlsx")
            return render(request, self.template_name, {"form": form})

        try:
            import openpyxl
            wb = openpyxl.load_workbook(uploaded, read_only=True, data_only=True)
            ws = wb.active
        except Exception as exc:
            logger.error("TaxpayerImport: cannot open workbook: %s", exc)
            messages.error(request, f"Не удалось открыть файл: {exc}")
            return render(request, self.template_name, {"form": form})

        created_count = 0
        updated_count = 0
        errors = []
        results = []

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        for row_num, row in enumerate(rows, start=2):
            if not any(row):
                continue

            iin_bin = str(row[0]).strip() if row[0] is not None else ""
            name = str(row[1]).strip() if row[1] is not None else ""
            type_raw = str(row[2]).strip().lower() if row[2] is not None else ""
            address = str(row[3]).strip() if row[3] is not None else ""
            phone = str(row[4]).strip() if row[4] is not None else ""
            email = str(row[5]).strip() if row[5] is not None else ""

            # Валидация обязательных полей
            if not iin_bin or not iin_bin.isdigit() or len(iin_bin) != 12:
                errors.append({"row": row_num, "iin_bin": iin_bin, "reason": "Некорректный ИИН/БИН"})
                continue
            if not name:
                errors.append({"row": row_num, "iin_bin": iin_bin, "reason": "Пустое наименование"})
                continue

            taxpayer_type = _TAXPAYER_TYPE_MAP.get(type_raw, TaxpayerType.LEGAL)

            try:
                obj, created = Taxpayer.objects.get_or_create(
                    iin_bin=iin_bin,
                    defaults={
                        "name": name,
                        "taxpayer_type": taxpayer_type,
                        "address": address,
                        "phone": phone,
                        "email": email,
                    },
                )
                if created:
                    created_count += 1
                    results.append({"row": row_num, "iin_bin": iin_bin, "name": name, "status": "создан"})
                else:
                    # Обновляем изменяемые поля
                    changed = False
                    for field, val in [("name", name), ("address", address), ("phone", phone), ("email", email)]:
                        if val and getattr(obj, field) != val:
                            setattr(obj, field, val)
                            changed = True
                    if changed:
                        obj.save(update_fields=["name", "address", "phone", "email"])
                        updated_count += 1
                        results.append({"row": row_num, "iin_bin": iin_bin, "name": name, "status": "обновлён"})
                    else:
                        results.append({"row": row_num, "iin_bin": iin_bin, "name": name, "status": "без изменений"})
            except Exception as exc:
                logger.error("TaxpayerImport row %d error: %s", row_num, exc)
                errors.append({"row": row_num, "iin_bin": iin_bin, "reason": str(exc)})

        audit_log(
            user=request.user,
            action="taxpayer_import",
            entity_type="taxpayer",
            entity_id=0,
            details={
                "filename": uploaded.name,
                "created": created_count,
                "updated": updated_count,
                "errors": len(errors),
            },
        )

        messages.success(
            request,
            f"Импорт завершён: создано {created_count}, обновлено {updated_count}, ошибок {len(errors)}."
        )
        return render(request, self.template_name, {
            "form": TaxpayerImportForm(),
            "results": results,
            "errors": errors,
            "created_count": created_count,
            "updated_count": updated_count,
        })


def taxpayer_import_template(request):
    """GET cases/taxpayers/import/template/ — отдаёт xlsx-шаблон для заполнения."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Налогоплательщики"

    headers = ["ИИН/БИН", "Наименование / ФИО", "Тип (ЮЛ/ФЛ/ИП)", "Адрес", "Телефон", "Email"]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font

    # Примеры данных
    examples = [
        ("123456789012", "ТОО «Пример»", "ЮЛ", "г. Алматы, ул. Примерная, 1", "+7 701 000 0000", "info@example.kz"),
        ("098765432109", "Иванов Иван Иванович", "ФЛ", "г. Нур-Султан, пр. Мира, 5", "+7 702 111 2233", ""),
        ("112233445566", "ИП Петров П.П.", "ИП", "", "+7 707 555 6677", "petrov@mail.kz"),
    ]
    for row_data in examples:
        ws.append(row_data)

    # Ширина колонок
    for col, width in enumerate([15, 35, 12, 35, 18, 25], start=1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width

    import io
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="taxpayer_import_template.xlsx"'
    return response


class ValidateIinView(LoginRequiredMixin, View):
    """POST cases/validate-iin/ — валидирует ИИН/БИН, возвращает JSON."""

    def post(self, request):
        from django.http import JsonResponse
        iin_bin = request.POST.get("iin_bin", "").strip()
        result = KZValidator.validate_iin_bin(iin_bin)
        if result.valid:
            return JsonResponse({
                "valid": True,
                "type": result.type,
                "metadata": result.metadata,
            })
        return JsonResponse({
            "valid": False,
            "error": IIN_BIN_ERRORS.get(result.error, "Неверный ИИН/БИН."),
        })
