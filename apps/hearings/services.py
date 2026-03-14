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
        protocol.file_path = doc.file_path
        protocol.save(update_fields=["file_path"])
    except ValueError as e:
        logger.warning("Protocol PDF not generated (no template?): %s", e)

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
