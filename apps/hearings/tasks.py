import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_protocol_deadline(self):
    """
    Устаревшая задача — делегирует в notifications.tasks.check_deadlines.
    Оставлена для совместимости; Beat расписание перенесено в check_deadlines.
    """
    from apps.notifications.tasks import check_deadlines
    return check_deadlines()
