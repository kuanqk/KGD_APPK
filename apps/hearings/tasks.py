import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_protocol_deadline(self):
    """
    Запускается каждый час через Celery Beat.
    Проверяет протоколы с истёкшим дедлайном 2 рабочих дней.
    Создаёт запись в AuditLog (полноценные Notification — Sprint 8).
    """
    from apps.hearings.models import HearingProtocol
    from apps.audit.services import audit_log
    from apps.cases.models import CaseStatus

    try:
        today = timezone.now().date()

        overdue_protocols = HearingProtocol.objects.filter(
            deadline_2days__lt=today,
            case__status=CaseStatus.PROTOCOL_CREATED,
        ).select_related("case", "case__responsible_user")

        count = 0
        for protocol in overdue_protocols:
            days_overdue = (today - protocol.deadline_2days).days
            audit_log(
                user=None,
                action="protocol_deadline_overdue",
                entity_type="protocol",
                entity_id=protocol.id,
                details={
                    "protocol_number": protocol.protocol_number,
                    "case_number": protocol.case.case_number,
                    "deadline": str(protocol.deadline_2days),
                    "days_overdue": days_overdue,
                    "responsible_user_id": (
                        protocol.case.responsible_user_id
                        if protocol.case.responsible_user_id
                        else None
                    ),
                },
            )
            logger.warning(
                "Protocol deadline overdue: %s case=%s overdue_days=%d",
                protocol.protocol_number,
                protocol.case.case_number,
                days_overdue,
            )
            count += 1

        logger.info("check_protocol_deadline: checked, %d overdue", count)
        return {"overdue_count": count, "checked_at": str(today)}

    except Exception as exc:
        logger.exception("check_protocol_deadline failed: %s", exc)
        raise self.retry(exc=exc)
