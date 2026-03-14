import logging
from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.cases.models import CaseStatus
from apps.cases.services import change_case_status
from apps.documents.models import CaseDocument
from .models import DeliveryMethod, DeliveryRecord, DeliveryStatus

logger = logging.getLogger(__name__)


@transaction.atomic
def create_delivery(
    document: CaseDocument,
    method: str,
    user,
    tracking_number: str = "",
    notes: str = "",
) -> DeliveryRecord:
    """
    Создаёт запись о доставке документа.
    Переводит дело в статус NOTICE_SENT.
    """
    delivery = DeliveryRecord.objects.create(
        case_document=document,
        method=method,
        status=DeliveryStatus.PENDING,
        tracking_number=tracking_number,
        notes=notes,
        sent_at=timezone.now(),
        created_by=user,
    )

    case = document.case
    from apps.cases.models import CaseEvent, CaseEventType

    method_label = dict(DeliveryMethod.choices).get(method, method)
    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.STATUS_CHANGED,
        description=f"Документ {document.doc_number} направлен НП ({method_label})"
        + (f", трек-номер: {tracking_number}" if tracking_number else ""),
        created_by=user,
    )

    if case.status in (CaseStatus.DRAFT, CaseStatus.NOTICE_CREATED):
        change_case_status(case, CaseStatus.NOTICE_SENT, user)

    audit_log(
        user=user,
        action="delivery_created",
        entity_type="delivery",
        entity_id=delivery.id,
        details={
            "doc_number": document.doc_number,
            "case_number": case.case_number,
            "method": method,
            "tracking_number": tracking_number,
        },
    )

    logger.info(
        "Delivery created: doc=%s case=%s method=%s by=%s",
        document.doc_number, case.case_number, method, user,
    )
    return delivery


@transaction.atomic
def mark_delivered(delivery: DeliveryRecord, user, notes: str = "") -> DeliveryRecord:
    """
    Фиксирует факт вручения документа.
    Переводит дело в статус DELIVERED.
    """
    delivery.status = DeliveryStatus.DELIVERED
    delivery.delivered_at = timezone.now()
    if notes:
        delivery.notes = notes
    delivery.result = "Вручено"
    delivery.save(update_fields=["status", "delivered_at", "notes", "result"])

    case = delivery.case
    from apps.cases.models import CaseEvent, CaseEventType

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.STATUS_CHANGED,
        description=(
            f"Документ {delivery.case_document.doc_number} вручён НП"
            f" ({delivery.get_method_display()})"
            + (f". {notes}" if notes else "")
        ),
        created_by=user,
    )

    if case.status not in (CaseStatus.DELIVERED, CaseStatus.HEARING_SCHEDULED,
                            CaseStatus.HEARING_DONE, CaseStatus.TERMINATED,
                            CaseStatus.COMPLETED, CaseStatus.ARCHIVED):
        change_case_status(case, CaseStatus.DELIVERED, user)

    audit_log(
        user=user,
        action="delivery_marked_delivered",
        entity_type="delivery",
        entity_id=delivery.id,
        details={
            "doc_number": delivery.case_document.doc_number,
            "case_number": case.case_number,
        },
    )

    logger.info("Delivery marked delivered: %s by %s", delivery.id, user)
    return delivery


@transaction.atomic
def mark_returned(delivery: DeliveryRecord, user, notes: str = "") -> DeliveryRecord:
    """
    Фиксирует возврат почтового отправления.
    Переводит дело в статус MAIL_RETURNED — Sprint 4 разблокирует кнопки.
    """
    delivery.status = DeliveryStatus.RETURNED
    delivery.returned_at = timezone.now()
    if notes:
        delivery.notes = notes
    delivery.result = "Возвращено"
    delivery.save(update_fields=["status", "returned_at", "notes", "result"])

    case = delivery.case
    from apps.cases.models import CaseEvent, CaseEventType

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.STATUS_CHANGED,
        description=(
            f"Почтовое отправление с документом {delivery.case_document.doc_number} возвращено"
            + (f". {notes}" if notes else "")
        ),
        created_by=user,
    )

    if case.status not in (CaseStatus.TERMINATED, CaseStatus.COMPLETED, CaseStatus.ARCHIVED):
        change_case_status(case, CaseStatus.MAIL_RETURNED, user)

    audit_log(
        user=user,
        action="delivery_marked_returned",
        entity_type="delivery",
        entity_id=delivery.id,
        details={
            "doc_number": delivery.case_document.doc_number,
            "case_number": case.case_number,
        },
    )

    logger.info("Delivery marked returned: %s by %s", delivery.id, user)
    return delivery
