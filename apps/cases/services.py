import logging
from datetime import date, timedelta
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import Now
from django.utils import timezone

from apps.audit.services import audit_log
from .models import AdministrativeCase, CaseEvent, CaseEventType, CaseStatus, Department, StagnationSettings, Taxpayer

logger = logging.getLogger(__name__)


def generate_case_number(department=None) -> str:
    """
    Генерирует номер дела формата АД-{КОД}-{YYYYMMDD}-{NNNNNNN}.
    Если офис не указан — fallback на старый формат АД-ГГГГ-NNNNN.
    """
    from django.db import transaction as db_transaction

    today = date.today()
    year = today.year

    if department is None:
        prefix = f"АД-{year}-"
        last = (
            AdministrativeCase.objects
            .filter(case_number__startswith=prefix)
            .order_by("-case_number")
            .values_list("case_number", flat=True)
            .first()
        )
        try:
            seq = int(last.split("-")[-1]) + 1 if last else 1
        except (ValueError, IndexError):
            seq = 1
        return f"{prefix}{seq:05d}"

    dept_code = str(department.code).zfill(2)
    date_str = today.strftime("%Y%m%d")

    with db_transaction.atomic():
        dept_obj = Department.objects.select_for_update().get(pk=department.pk)
        if dept_obj.case_seq_year != year:
            dept_obj.case_seq_year = year
            dept_obj.case_sequence = 1
        else:
            dept_obj.case_sequence += 1
        dept_obj.save(update_fields=["case_sequence", "case_seq_year"])
        seq = dept_obj.case_sequence

    return f"АД-{dept_code}-{date_str}-{seq:07d}"


@transaction.atomic
def create_case(
    operator,
    taxpayer_data: dict,
    region=None,
    basis=None,
    department=None,
    category=None,
    description: str = "",
    responsible_user=None,
) -> AdministrativeCase:
    """Создаёт новое административное дело."""
    taxpayer, _ = Taxpayer.objects.get_or_create(
        iin_bin=taxpayer_data["iin_bin"],
        defaults={
            "name": taxpayer_data["name"],
            "taxpayer_type": taxpayer_data.get("taxpayer_type", "legal"),
            "address": taxpayer_data.get("address", ""),
            "phone": taxpayer_data.get("phone", ""),
            "email": taxpayer_data.get("email", ""),
        },
    )

    case = AdministrativeCase.objects.create(
        case_number=generate_case_number(department),
        taxpayer=taxpayer,
        region=region,
        department=department,  # FK: Department instance or None
        basis=basis,
        category=category,
        description=description,
        responsible_user=responsible_user,
        created_by=operator,
        status=CaseStatus.DRAFT,
    )

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.CREATED,
        description=f"Дело создано оператором {operator}",
        created_by=operator,
    )

    audit_log(
        user=operator,
        action="case_created",
        entity_type="case",
        entity_id=case.id,
        details={"case_number": case.case_number, "taxpayer_iin": taxpayer.iin_bin},
    )

    # Уведомляем ответственного о назначении только если он имеет доступ к делу
    can_notify = (
        responsible_user
        and responsible_user != operator
        and (
            responsible_user.role in ("admin", "reviewer")
            or responsible_user.department == department
        )
    )
    if can_notify:
        try:
            from django.urls import reverse
            from apps.notifications.models import NotificationType
            from apps.notifications.services import notify
            notify(
                user=responsible_user,
                notification_type=NotificationType.ASSIGNED,
                message=f"Вам назначено дело {case.case_number} ({case.taxpayer.name}).",
                case=case,
                url=reverse("cases:detail", kwargs={"pk": case.pk}),
            )
        except Exception:
            logger.exception("create_case: failed to notify responsible_user")

    logger.info("Case created: %s by %s", case.case_number, operator)
    return case


@transaction.atomic
def change_case_status(case: AdministrativeCase, new_status: str, user, comment: str = "") -> AdministrativeCase:
    """Меняет статус дела, создаёт событие и пишет в аудит."""
    old_status = case.status
    case.status = new_status

    case.last_activity_at = timezone.now()
    update_fields = ["status", "last_activity_at", "updated_at"]
    if new_status in (CaseStatus.TERMINATED, CaseStatus.COMPLETED, CaseStatus.ARCHIVED):
        case.closed_at = timezone.now()
        update_fields.append("closed_at")
    case.save(update_fields=update_fields)

    description = f"Статус изменён: «{CaseStatus(old_status).label}» → «{CaseStatus(new_status).label}»"
    if comment:
        description += f". Комментарий: {comment}"

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.STATUS_CHANGED,
        description=description,
        created_by=user,
    )

    audit_log(
        user=user,
        action="status_changed",
        entity_type="case",
        entity_id=case.id,
        details={"from": old_status, "to": new_status, "comment": comment},
    )

    logger.info("Case %s status: %s → %s by %s", case.case_number, old_status, new_status, user)
    return case


@transaction.atomic
def allow_backdating(case: AdministrativeCase, user, comment: str) -> AdministrativeCase:
    """Разрешает ввод документов задним числом по делу. Только admin и reviewer."""
    if user.role not in ("admin", "reviewer"):
        raise PermissionDenied("Разрешить ввод задним числом может только администратор или руководитель.")

    case.allow_backdating = True
    case.backdating_allowed_by = user
    case.backdating_allowed_at = timezone.now()
    case.backdating_comment = comment
    case.save(update_fields=[
        "allow_backdating", "backdating_allowed_by",
        "backdating_allowed_at", "backdating_comment", "updated_at",
    ])

    audit_log(
        user=user,
        action="backdating_allowed",
        entity_type="case",
        entity_id=case.id,
        details={"case_number": case.case_number, "comment": comment},
    )

    logger.info("Backdating allowed for case %s by %s", case.case_number, user)
    return case


def validate_document_date(case: AdministrativeCase, document_date: date) -> None:
    """
    Проверяет что дата документа не раньше даты открытия дела.
    Исключение — если backdating явно разрешён.
    """
    case_open_date = case.created_at.date()
    if document_date < case_open_date and not case.allow_backdating:
        raise ValueError(
            f"Дата документа ({document_date:%d.%m.%Y}) раньше даты открытия дела "
            f"({case_open_date:%d.%m.%Y}). Для ввода задним числом требуется разрешение."
        )


def after_return_actions(case: AdministrativeCase, doc_type: str, user) -> AdministrativeCase:
    """
    Управляет прогрессией статусов после возврата почтового отправления.

    MAIL_RETURNED → (акт) → ACT_CREATED → (ДЭР) → DER_SENT

    Вызывается из views после успешной генерации документа.
    Бизнес-правило: кнопка "Запрос в ДЭР" активна только при ACT_CREATED.
    """
    from apps.documents.models import DocumentType

    if doc_type == DocumentType.INSPECTION_ACT:
        if case.status == CaseStatus.MAIL_RETURNED:
            change_case_status(
                case, CaseStatus.ACT_CREATED, user,
                comment="Акт налогового обследования оформлен",
            )
    elif doc_type == DocumentType.DER_REQUEST:
        if case.status == CaseStatus.ACT_CREATED:
            change_case_status(
                case, CaseStatus.DER_SENT, user,
                comment="Запрос в ДЭР об оказании содействия направлен",
            )

    audit_log(
        user=user,
        action="return_action_taken",
        entity_type="case",
        entity_id=case.id,
        details={"doc_type": doc_type, "new_status": case.status},
    )
    return case


FINAL_STATUSES = frozenset({CaseStatus.TERMINATED, CaseStatus.COMPLETED, CaseStatus.ARCHIVED})


def get_stagnant_cases():
    """
    Возвращает QS активных дел, у которых последняя активность
    старше порога (StagnationSettings.stagnation_days).
    """
    settings_obj = StagnationSettings.get()
    threshold_dt = timezone.now() - timedelta(days=settings_obj.stagnation_days)
    return (
        AdministrativeCase.objects
        .exclude(status__in=FINAL_STATUSES)
        .filter(last_activity_at__lt=threshold_dt)
        .select_related("responsible_user", "department", "taxpayer")
    )


def get_dashboard_data(user) -> dict:
    """
    Возвращает данные для дашборда в зависимости от роли пользователя.
    Вся бизнес-логика изолирована здесь, view остаётся тонким.
    """
    settings_obj = StagnationSettings.get()
    threshold_dt = timezone.now() - timedelta(days=settings_obj.stagnation_days)
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)

    stagnant_annotation = ExpressionWrapper(
        Now() - F("last_activity_at"),
        output_field=DurationField(),
    )

    if user.role in ("admin", "reviewer"):
        # ── Агрегация по офисам ────────────────────────────────────────────
        dept_stats = Department.objects.annotate(
            total=Count("cases"),
            active=Count(
                "cases",
                filter=Q(cases__status__in=[
                    s for s in CaseStatus.values if s not in FINAL_STATUSES
                ]),
            ),
            stagnant=Count(
                "cases",
                filter=Q(
                    cases__status__in=[
                        s for s in CaseStatus.values if s not in FINAL_STATUSES
                    ],
                    cases__last_activity_at__lt=threshold_dt,
                ),
            ),
            pending_approval=Count(
                "cases",
                filter=Q(cases__final_decision__status="pending_approval"),
            ),
        ).order_by("code")

        # ── Топ-5 застывших дел ────────────────────────────────────────────
        top_stagnant = (
            AdministrativeCase.objects
            .exclude(status__in=FINAL_STATUSES)
            .filter(last_activity_at__lt=threshold_dt)
            .annotate(days_stagnant=stagnant_annotation)
            .select_related("taxpayer", "responsible_user", "department")
            .order_by("-days_stagnant")[:5]
        )

        # ── Счётчики статусов по всей системе ─────────────────────────────
        all_cases = AdministrativeCase.objects
        status_counts = {
            "draft": all_cases.filter(status=CaseStatus.DRAFT).count(),
            "active": all_cases.exclude(status__in=FINAL_STATUSES).exclude(
                status=CaseStatus.DRAFT
            ).count(),
            "completed": all_cases.filter(
                status__in=[CaseStatus.TERMINATED, CaseStatus.COMPLETED, CaseStatus.AUDIT_APPROVED]
            ).count(),
            "archived": all_cases.filter(status=CaseStatus.ARCHIVED).count(),
        }

        return {
            "role_group": "admin_reviewer",
            "dept_stats": dept_stats,
            "top_stagnant": top_stagnant,
            "status_counts": status_counts,
            "stagnation_threshold": settings_obj.stagnation_days,
        }

    if user.role in ("operator", "executor"):
        from apps.hearings.models import Hearing, HearingProtocol, HearingStatus

        # ── Мои активные дела ──────────────────────────────────────────────
        my_cases = (
            AdministrativeCase.objects
            .filter(responsible_user=user)
            .exclude(status__in=FINAL_STATUSES)
            .annotate(days_stagnant=stagnant_annotation)
            .select_related("taxpayer", "department")
            .order_by("last_activity_at")[:15]
        )

        # ── Заслушивания сегодня и завтра ──────────────────────────────────
        upcoming_hearings = (
            Hearing.objects
            .filter(
                case__responsible_user=user,
                hearing_date__in=[today, tomorrow],
                status__in=[HearingStatus.SCHEDULED, HearingStatus.IN_PROGRESS],
            )
            .select_related("case", "case__taxpayer")
            .order_by("hearing_date", "hearing_time")
        )

        # ── Дедлайны протоколов сегодня и завтра ──────────────────────────
        protocol_deadlines = (
            HearingProtocol.objects
            .filter(
                case__responsible_user=user,
                deadline_2days__in=[today, tomorrow],
                case__status=CaseStatus.PROTOCOL_CREATED,
            )
            .select_related("case", "case__taxpayer")
            .order_by("deadline_2days")
        )

        # ── Дела, ожидающие действий ───────────────────────────────────────
        ACTION_STATUSES = [
            CaseStatus.DRAFT,
            CaseStatus.NOTICE_CREATED,
            CaseStatus.DELIVERED,
            CaseStatus.MAIL_RETURNED,
            CaseStatus.ACT_CREATED,
            CaseStatus.HEARING_DONE,
            CaseStatus.PROTOCOL_CREATED,
        ]
        awaiting_action = (
            AdministrativeCase.objects
            .filter(responsible_user=user, status__in=ACTION_STATUSES)
            .select_related("taxpayer")
            .order_by("last_activity_at")[:10]
        )

        return {
            "role_group": "operator_executor",
            "my_cases": my_cases,
            "upcoming_hearings": upcoming_hearings,
            "protocol_deadlines": protocol_deadlines,
            "awaiting_action": awaiting_action,
            "today": today,
            "tomorrow": tomorrow,
            "stagnation_threshold": settings_obj.stagnation_days,
        }

    # ── observer ───────────────────────────────────────────────────────────────
    region_qs = AdministrativeCase.objects.filter(region__name=user.region)
    from django.db.models import Count as _Count
    raw_counts = region_qs.values("status").annotate(count=_Count("id"))
    status_counts = {row["status"]: row["count"] for row in raw_counts}

    total = region_qs.count()
    active = region_qs.exclude(status__in=FINAL_STATUSES).count()
    stagnant_count = region_qs.exclude(status__in=FINAL_STATUSES).filter(
        last_activity_at__lt=threshold_dt
    ).count()

    return {
        "role_group": "observer",
        "region": user.region,
        "total": total,
        "active": active,
        "stagnant_count": stagnant_count,
        "status_counts": status_counts,
        "stagnation_threshold": settings_obj.stagnation_days,
    }
