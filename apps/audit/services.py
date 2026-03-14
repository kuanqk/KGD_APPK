import logging
from typing import Optional

logger = logging.getLogger(__name__)


def audit_log(
    user,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Записывает действие пользователя в AuditLog.
    Вызывать после каждой мутации данных.
    """
    from .models import AuditLog

    try:
        AuditLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
        )
    except Exception:
        logger.exception(
            "Failed to write audit log: action=%s entity_type=%s entity_id=%s",
            action,
            entity_type,
            entity_id,
        )
