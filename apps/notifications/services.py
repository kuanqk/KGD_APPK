import logging
from typing import Optional

from django.db import transaction

logger = logging.getLogger(__name__)


def notify(
    user,
    notification_type: str,
    message: str,
    case=None,
    url: str = "",
) -> "Notification":
    """
    Создаёт одно уведомление для пользователя.
    Если у пользователя есть email — ставит в очередь на отправку.
    """
    from .models import Notification
    n = Notification.objects.create(
        user=user,
        case=case,
        notification_type=notification_type,
        message=message,
        url=url,
    )
    logger.debug("Notification created: user=%s type=%s", user, notification_type)
    return n


def notify_many(
    users,
    notification_type: str,
    message: str,
    case=None,
    url: str = "",
) -> int:
    """
    Создаёт уведомления для нескольких пользователей через bulk_create.
    Возвращает количество созданных записей.
    """
    from .models import Notification
    objects = [
        Notification(
            user=u,
            case=case,
            notification_type=notification_type,
            message=message,
            url=url,
        )
        for u in users
        if u is not None
    ]
    if not objects:
        return 0
    created = Notification.objects.bulk_create(objects)
    logger.debug("notify_many: created %d notifications type=%s", len(created), notification_type)
    return len(created)


def mark_read(notification, user) -> None:
    """Помечает одно уведомление как прочитанное (только владелец)."""
    from .models import Notification
    if notification.user_id != user.pk:
        return
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])


def mark_all_read(user) -> int:
    """Помечает все непрочитанные уведомления пользователя как прочитанные."""
    from .models import Notification
    updated = (
        Notification.objects
        .for_user(user)
        .unread()
        .update(is_read=True)
    )
    logger.debug("mark_all_read: user=%s updated=%d", user, updated)
    return updated
