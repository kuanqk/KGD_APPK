import logging
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.cases.models import CaseEvent, CaseEventType, CaseStatus
from apps.cases.services import change_case_status
from .models import Hearing, HearingProtocol, HearingStatus

logger = logging.getLogger(__name__)

# Статусы, при которых можно назначить заслушивание
HEARING_ALLOWED_STATUSES = (
    CaseStatus.DELIVERED,
    CaseStatus.MAIL_RETURNED,
    CaseStatus.ACT_CREATED,
    CaseStatus.DER_SENT,
)


def calc_working_deadline(start: date, days: int = 2) -> date:
    """Вычисляет дату дедлайна, пропуская субботу и воскресенье."""
    current = start
    counted = 0
    while counted < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # 0=Пн, 4=Пт
            counted += 1
    return current


def _generate_protocol_number() -> str:
    """Генерирует номер протокола формата ПРТ-ГГГГ-NNNNN."""
    year = date.today().year
    prefix = f"ПРТ-{year}-"
    last = (
        HearingProtocol.objects
        .filter(protocol_number__startswith=prefix)
        .order_by("-protocol_number")
        .values_list("protocol_number", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    return f"{prefix}{seq:05d}"


@transaction.atomic
def schedule_hearing(
    case,
    hearing_date: date,
    location: str,
    user,
    hearing_time=None,
    format: str = "in_person",
    participants: list = None,
    notes: str = "",
) -> Hearing:
    """Назначает заслушивание по делу."""
    hearing = Hearing.objects.create(
        case=case,
        hearing_date=hearing_date,
        hearing_time=hearing_time,
        location=location,
        format=format,
        participants=participants or [],
        notes=notes,
        created_by=user,
        status=HearingStatus.SCHEDULED,
    )

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.HEARING_SCHEDULED,
        description=(
            f"Заслушивание назначено на {hearing_date:%d.%m.%Y}"
            + (f" {hearing_time:%H:%M}" if hearing_time else "")
            + f", место: {location}"
        ),
        created_by=user,
    )

    change_case_status(case, CaseStatus.HEARING_SCHEDULED, user)

    audit_log(
        user=user,
        action="hearing_scheduled",
        entity_type="hearing",
        entity_id=hearing.id,
        details={
            "case_number": case.case_number,
            "hearing_date": str(hearing_date),
            "location": location,
        },
    )

    # Уведомляем ответственного и участников о назначении заслушивания
    try:
        from django.urls import reverse
        from apps.notifications.models import NotificationType
        from apps.notifications.services import notify, notify_many
        from apps.accounts.models import User

        url = reverse("cases:detail", kwargs={"pk": case.pk})
        msg = (
            f"Заслушивание по делу {case.case_number} назначено "
            f"на {hearing_date:%d.%m.%Y}"
            + (f" {hearing_time:%H:%M}" if hearing_time else "")
            + f", место: {location}."
        )

        to_notify = set()
        if case.responsible_user and case.responsible_user != user:
            to_notify.add(case.responsible_user)

        # Участники — список user_id, если переданы
        if participants:
            part_users = list(User.objects.filter(pk__in=participants))
            to_notify.update(u for u in part_users if u != user)

        if to_notify:
            notify_many(
                users=list(to_notify),
                notification_type=NotificationType.ASSIGNED,
                message=msg,
                case=case,
                url=url,
            )
    except Exception:
        logger.exception("schedule_hearing: failed to notify participants")

    logger.info("Hearing scheduled: case=%s date=%s by=%s", case.case_number, hearing_date, user)
    return hearing


@transaction.atomic
def complete_hearing(hearing: Hearing, user) -> Hearing:
    """Фиксирует факт проведения заслушивания."""
    hearing.status = HearingStatus.COMPLETED
    hearing.save(update_fields=["status"])

    CaseEvent.objects.create(
        case=hearing.case,
        event_type=CaseEventType.STATUS_CHANGED,
        description=f"Заслушивание от {hearing.hearing_date:%d.%m.%Y} проведено",
        created_by=user,
    )

    change_case_status(hearing.case, CaseStatus.HEARING_DONE, user)

    audit_log(
        user=user,
        action="hearing_completed",
        entity_type="hearing",
        entity_id=hearing.id,
        details={"case_number": hearing.case.case_number},
    )

    logger.info("Hearing completed: %s by %s", hearing.id, user)
    return hearing


@transaction.atomic
def create_protocol(
    hearing: Hearing,
    result_summary: str,
    user,
) -> HearingProtocol:
    """
    Оформляет протокол заслушивания:
    1. Создаёт HearingProtocol
    2. Генерирует PDF через DocumentTemplate
    3. Вычисляет дедлайн 2 рабочих дня
    4. Переводит дело в PROTOCOL_CREATED
    """
    if hasattr(hearing, "protocol"):
        raise ValueError("Протокол для этого заслушивания уже оформлен.")

    today = date.today()
    deadline = calc_working_deadline(today, days=2)
    protocol_number = _generate_protocol_number()

    protocol = HearingProtocol.objects.create(
        case=hearing.case,
        hearing=hearing,
        protocol_number=protocol_number,
        protocol_date=today,
        result_summary=result_summary,
        deadline_2days=deadline,
        created_by=user,
    )

    # Генерируем PDF протокола через документную систему
    try:
        from apps.documents.models import DocumentType
        from apps.documents.services import generate_document
        doc = generate_document(hearing.case, DocumentType.HEARING_PROTOCOL, user)
        if not doc or not doc.pk:
            logger.error(
                "create_protocol: generate_document вернул документ без pk (case=%s)",
                hearing.case.case_number,
            )
            raise ValueError("Документ протокола не был сохранён (doc.pk is None).")
        protocol.file_path = doc.file_path
        protocol.save(update_fields=["file_path"])
        logger.info(
            "Protocol document saved: doc.pk=%s file_path=%s", doc.pk, doc.file_path
        )
    except ValueError as e:
        logger.error(
            "create_protocol: PDF не сгенерирован для case=%s: %s",
            hearing.case.case_number, e,
        )
        raise

    CaseEvent.objects.create(
        case=hearing.case,
        event_type=CaseEventType.DECISION_MADE,
        description=(
            f"Протокол заслушивания {protocol_number} оформлен. "
            f"Дедлайн решения: {deadline:%d.%m.%Y} (2 рабочих дня)"
        ),
        created_by=user,
    )

    change_case_status(hearing.case, CaseStatus.PROTOCOL_CREATED, user)

    audit_log(
        user=user,
        action="protocol_created",
        entity_type="protocol",
        entity_id=protocol.id,
        details={
            "protocol_number": protocol_number,
            "case_number": hearing.case.case_number,
            "deadline": str(deadline),
        },
    )

    logger.info(
        "Protocol created: %s for case %s deadline=%s by %s",
        protocol_number, hearing.case.case_number, deadline, user,
    )
    return protocol
