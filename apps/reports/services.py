"""
Сервисы отчётности АППК.
Все функции принимают словарь filters и пользователя,
возвращают QuerySet или dict — никакой логики рендеринга здесь нет.
"""
import logging
from datetime import timedelta

from django.db.models import Avg, Count, F, ExpressionWrapper, DurationField, Q
from django.utils import timezone

from apps.cases.models import AdministrativeCase, CaseStatus

logger = logging.getLogger(__name__)


# ─── Вспомогательная функция применения фильтров ────────────────────────────

def apply_filters(qs, filters: dict, user):
    """
    Применяет стандартный набор фильтров к QuerySet дел.
    filters keys: date_from, date_to, region, department,
                  status, responsible_user
    Всегда применяет for_user() для изоляции данных.
    """
    qs = qs.for_user(user)

    if filters.get("date_from"):
        qs = qs.filter(created_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(created_at__date__lte=filters["date_to"])
    if filters.get("region"):
        qs = qs.filter(region__icontains=filters["region"])
    if filters.get("department"):
        qs = qs.filter(department__icontains=filters["department"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("responsible_user"):
        qs = qs.filter(responsible_user=filters["responsible_user"])

    return qs


# ─── Отчёты ─────────────────────────────────────────────────────────────────

def cases_by_status(filters: dict, user) -> dict:
    """Количество дел по каждому статусу."""
    qs = apply_filters(AdministrativeCase.objects, filters, user)
    rows = qs.values("status").annotate(count=Count("id")).order_by("status")
    result = {}
    for row in rows:
        label = CaseStatus(row["status"]).label if row["status"] in CaseStatus.values else row["status"]
        result[label] = row["count"]
    return result


def cases_by_region(filters: dict, user) -> dict:
    """Количество дел по регионам."""
    qs = apply_filters(AdministrativeCase.objects, filters, user)
    rows = qs.values("region").annotate(count=Count("id")).order_by("-count")
    return {row["region"]: row["count"] for row in rows}


def overdue_cases(filters: dict, user):
    """
    Дела с просроченным дедлайном протокола (2 рабочих дня).
    Возвращает QS дел с аннотацией days_overdue.
    """
    from apps.hearings.models import HearingProtocol
    today = timezone.now().date()

    overdue_case_ids = (
        HearingProtocol.objects
        .filter(deadline_2days__lt=today, case__status=CaseStatus.PROTOCOL_CREATED)
        .values_list("case_id", flat=True)
    )

    qs = apply_filters(AdministrativeCase.objects, filters, user)
    return (
        qs.filter(pk__in=overdue_case_ids)
        .select_related("taxpayer", "responsible_user")
        .prefetch_related("protocols")
        .order_by("protocols__deadline_2days")
    )


def terminated_cases(filters: dict, user):
    """Прекращённые дела."""
    filters_copy = dict(filters)
    filters_copy["status"] = CaseStatus.TERMINATED
    qs = apply_filters(AdministrativeCase.objects, filters_copy, user)
    return (
        qs.select_related("taxpayer", "responsible_user", "final_decision")
        .order_by("-closed_at")
    )


def audit_initiated_cases(filters: dict, user):
    """Дела с назначенной внеплановой проверкой."""
    filters_copy = dict(filters)
    filters_copy["status"] = CaseStatus.AUDIT_APPROVED
    qs = apply_filters(AdministrativeCase.objects, filters_copy, user)
    return (
        qs.select_related("taxpayer", "responsible_user", "final_decision")
        .order_by("-closed_at")
    )


def avg_case_duration(filters: dict, user) -> dict:
    """
    Среднее время жизни закрытых дел (от created_at до closed_at).
    Возвращает dict с ключами: avg_days, total_closed, by_status.
    """
    qs = apply_filters(AdministrativeCase.objects, filters, user)
    closed = qs.filter(closed_at__isnull=False)

    duration_expr = ExpressionWrapper(
        F("closed_at") - F("created_at"),
        output_field=DurationField(),
    )
    agg = closed.annotate(duration=duration_expr).aggregate(avg_dur=Avg("duration"))
    avg_td = agg["avg_dur"] or timedelta(0)

    by_status = {}
    for status in (CaseStatus.TERMINATED, CaseStatus.AUDIT_APPROVED, CaseStatus.COMPLETED, CaseStatus.ARCHIVED):
        sub = closed.filter(status=status).annotate(duration=duration_expr).aggregate(avg_dur=Avg("duration"))
        td = sub["avg_dur"] or timedelta(0)
        by_status[CaseStatus(status).label] = round(td.total_seconds() / 86400, 1)

    return {
        "avg_days": round(avg_td.total_seconds() / 86400, 1),
        "total_closed": closed.count(),
        "by_status": by_status,
    }


def revision_journal(filters: dict, user):
    """
    Журнал возвратов на доработку: все ApprovalFlow с result=RETURNED.
    Фильтр по дате применяется к sent_at.
    """
    from apps.approvals.models import ApprovalFlow, ApprovalResult

    qs = ApprovalFlow.objects.filter(result=ApprovalResult.RETURNED)

    if filters.get("date_from"):
        qs = qs.filter(sent_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(sent_at__date__lte=filters["date_to"])

    # Изоляция: reviewer/admin видит всё, остальные — только свои
    if user.role not in ("admin", "reviewer"):
        qs = qs.filter(sent_by=user)

    return qs.select_related("sent_by", "reviewed_by").order_by("-reviewed_at")


def discipline_report(filters: dict, user) -> list:
    """
    Дисциплинарный отчёт по ответственным:
    {user, assigned_count, overdue_count, completed_count}
    Возвращает list[dict] отсортированный по overdue_count desc.
    """
    from django.contrib.auth import get_user_model
    from apps.hearings.models import HearingProtocol

    User = get_user_model()
    today = timezone.now().date()

    base_qs = apply_filters(AdministrativeCase.objects, filters, user)

    overdue_ids = set(
        HearingProtocol.objects
        .filter(deadline_2days__lt=today, case__status=CaseStatus.PROTOCOL_CREATED)
        .values_list("case_id", flat=True)
    )

    completed_statuses = {
        CaseStatus.TERMINATED, CaseStatus.AUDIT_APPROVED,
        CaseStatus.COMPLETED, CaseStatus.ARCHIVED,
    }

    users = (
        User.objects
        .filter(responsible_cases__in=base_qs)
        .distinct()
        .order_by("last_name", "first_name")
    )

    result = []
    for u in users:
        user_cases = base_qs.filter(responsible_user=u)
        assigned = user_cases.count()
        overdue = user_cases.filter(pk__in=overdue_ids).count()
        completed = user_cases.filter(status__in=completed_statuses).count()
        result.append({
            "user": u,
            "assigned": assigned,
            "overdue": overdue,
            "completed": completed,
        })

    result.sort(key=lambda r: -r["overdue"])
    return result


def cases_registry(filters: dict, user):
    """
    Полный реестр дел для выгрузки.
    Все поля через select_related + prefetch_related.
    """
    qs = apply_filters(AdministrativeCase.objects, filters, user)
    return (
        qs.select_related("taxpayer", "responsible_user", "created_by")
        .prefetch_related("documents", "hearings", "events")
        .order_by("-created_at")
    )
