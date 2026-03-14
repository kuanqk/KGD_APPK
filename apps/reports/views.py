import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import TemplateView, View

from apps.audit.services import audit_log
from .exporters import REPORT_META, export_pdf, export_xlsx
from .forms import ReportFilterForm
from . import services as svc

logger = logging.getLogger(__name__)

# Упорядоченный список карточек дашборда
DASHBOARD_REPORTS = [
    ("cases_by_status",      "bi-pie-chart",         "Дела по статусам",              "Распределение дел по текущему статусу"),
    ("cases_by_region",      "bi-geo-alt",           "Дела по регионам",              "Количество дел в каждом регионе"),
    ("overdue_cases",        "bi-exclamation-triangle","Просроченные дела",            "Дела с истёкшим 2-рабочим дедлайном"),
    ("terminated_cases",     "bi-x-circle",          "Прекращённые дела",             "Дела завершённые прекращением"),
    ("audit_initiated_cases","bi-search",            "Проверки назначены",            "Дела с назначенной внеплановой проверкой"),
    ("avg_case_duration",    "bi-clock-history",     "Среднее время жизни",           "Среднее от создания до закрытия дела"),
    ("revision_journal",     "bi-arrow-return-left", "Журнал возвратов",              "Все решения, возвращённые на доработку"),
    ("discipline_report",    "bi-person-badge",      "Дисциплинарный отчёт",          "Статистика по ответственным сотрудникам"),
    ("cases_registry",       "bi-table",             "Реестр дел",                    "Полный реестр дел для выгрузки"),
]


class ReportDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "reports/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = DASHBOARD_REPORTS
        return context


class ReportDetailView(LoginRequiredMixin, TemplateView):
    template_name = "reports/detail.html"

    def _get_report_type(self):
        rt = self.kwargs.get("report_type")
        if rt not in REPORT_META:
            raise Http404(f"Отчёт '{rt}' не найден.")
        return rt

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_type = self._get_report_type()
        meta = REPORT_META[report_type]

        form = ReportFilterForm(self.request.GET or None)
        filters = form.get_filters() if self.request.GET else {}

        data = None
        rows = []
        error = None

        try:
            fn_map = {
                "cases_by_status": svc.cases_by_status,
                "cases_by_region": svc.cases_by_region,
                "overdue_cases": svc.overdue_cases,
                "terminated_cases": svc.terminated_cases,
                "audit_initiated_cases": svc.audit_initiated_cases,
                "avg_case_duration": svc.avg_case_duration,
                "revision_journal": svc.revision_journal,
                "discipline_report": svc.discipline_report,
                "cases_registry": svc.cases_registry,
            }
            data = fn_map[report_type](filters, self.request.user)

            # Для QS — материализуем первые 500 строк
            from django.db.models import QuerySet
            if isinstance(data, QuerySet):
                data = list(data[:500])

            audit_log(
                user=self.request.user,
                action="report_viewed",
                entity_type="report",
                details={"report_type": report_type, "filters": str(filters)},
            )
        except Exception as exc:
            logger.exception("ReportDetailView error: %s", exc)
            error = str(exc)

        context.update({
            "report_type": report_type,
            "meta": meta,
            "form": form,
            "data": data,
            "error": error,
            "can_export": True,
        })
        return context


class ExportView(LoginRequiredMixin, View):
    """GET /reports/<report_type>/export/?format=pdf|xlsx"""

    def get(self, request, report_type):
        if report_type not in REPORT_META:
            raise Http404

        fmt = request.GET.get("format", "xlsx").lower()
        form = ReportFilterForm(request.GET)
        filters = form.get_filters()

        try:
            if fmt == "pdf":
                return export_pdf(report_type, filters, request.user)
            else:
                return export_xlsx(report_type, filters, request.user)
        except ValueError as exc:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, str(exc))
            return redirect("reports:detail", report_type=report_type)
