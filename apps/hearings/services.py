import logging
from datetime import date, datetime, time, timedelta

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
    """Вычисляет дату, отстоящую на ``days`` рабочих дней от ``start`` (без сб/вс)."""
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


def _hearing_protocol_form_data_from_hearing(hearing: Hearing, result_summary: str, user) -> dict:
    """Данные для generate_hearing_protocol из заслушивания (место, дата, время, итог)."""
    ht = hearing.hearing_time
    if ht:
        start = ht
        end = (datetime.combine(hearing.hearing_date, ht) + timedelta(hours=1)).time()
    else:
        start = time(9, 0)
        end = time(10, 0)
    full_name = user.get_full_name() or ""
    summary = (result_summary or "").strip() or "—"
    return {
        "venue": (hearing.location or "").strip(),
        "hearing_date": hearing.hearing_date,
        "time_start": start,
        "time_end": end,
        "official_name": full_name,
        "secretary_name": "",
        "participant_info": summary,
        "participant_position": "",
        "dgd_position": "",
        "signatory_name": full_name,
        "acquainted_name": "",
        "decision_text": "",
    }


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
    2. Генерирует PDF через интерактивный шаблон протокола (дата, место, итоги)
    3. Вычисляет крайний срок: 3 рабочих дня на замечания к протоколу (п. 6 ст. 74 АППК)
    4. Переводит дело в PROTOCOL_CREATED
    """
    if hasattr(hearing, "protocol"):
        raise ValueError("Протокол для этого заслушивания уже оформлен.")

    today = date.today()
    deadline = calc_working_deadline(today, days=3)
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

    try:
        from apps.documents.services import generate_hearing_protocol

        form_data = _hearing_protocol_form_data_from_hearing(hearing, result_summary, user)
        doc = generate_hearing_protocol(hearing.case, form_data, user)
        if not doc or not doc.pk:
            logger.error(
                "create_protocol: generate_hearing_protocol вернул документ без pk (case=%s)",
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
            f"Крайний срок замечаний к протоколу (3 рабочих дня, п. 6 ст. 74 АППК): {deadline:%d.%m.%Y}"
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
