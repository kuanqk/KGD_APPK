import logging
from datetime import date
from django.db import transaction

from apps.audit.services import audit_log
from .models import AdministrativeCase, CaseEvent, CaseEventType, CaseStatus, Taxpayer

logger = logging.getLogger(__name__)


def generate_case_number() -> str:
    """Генерирует номер дела формата АД-ГГГГ-NNNNN."""
    year = date.today().year
    prefix = f"АД-{year}-"
    last = (
        AdministrativeCase.objects
        .filter(case_number__startswith=prefix)
        .order_by("-case_number")
        .values_list("case_number", flat=True)
        .first()
    )
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


@transaction.atomic
def create_case(
    operator,
    taxpayer_data: dict,
    region: str,
    basis: str,
    department: str = "",
    category: str = "",
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
        case_number=generate_case_number(),
        taxpayer=taxpayer,
        region=region,
        department=department,
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

    # Уведомляем ответственного о назначении
    if responsible_user and responsible_user != operator:
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

    if new_status in (CaseStatus.TERMINATED, CaseStatus.COMPLETED, CaseStatus.ARCHIVED):
        from django.utils import timezone
        case.closed_at = timezone.now()

    case.save(update_fields=["status", "closed_at", "updated_at"] if case.closed_at else ["status", "updated_at"])

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
