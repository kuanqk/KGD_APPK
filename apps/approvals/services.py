import logging
from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from .models import ApprovalFlow, ApprovalResult, EntityType

logger = logging.getLogger(__name__)


def _entity_type_for(entity) -> str:
    """Определяет entity_type строку по классу объекта."""
    from apps.decisions.models import FinalDecision
    from apps.documents.models import CaseDocument
    from apps.cases.models import AdministrativeCase

    if isinstance(entity, FinalDecision):
        return EntityType.DECISION
    if isinstance(entity, CaseDocument):
        return EntityType.DOCUMENT
    if isinstance(entity, AdministrativeCase):
        return EntityType.CASE
    raise ValueError(f"Неизвестный тип сущности: {type(entity)}")


def _next_version(entity_type: str, entity_id: int) -> int:
    last = (
        ApprovalFlow.objects
        .filter(entity_type=entity_type, entity_id=entity_id)
        .order_by("-version")
        .values_list("version", flat=True)
        .first()
    )
    return (last or 0) + 1


def get_history(entity) -> "QuerySet[ApprovalFlow]":
    """Все итерации согласования для сущности, от первой к последней."""
    entity_type = _entity_type_for(entity)
    return ApprovalFlow.objects.for_entity(entity_type, entity.id)


def _notify_reviewers(message: str, case=None, url: str = "") -> None:
    """Уведомляет всех активных reviewer/admin о новом согласовании."""
    from apps.accounts.models import User
    from apps.notifications.models import NotificationType
    from apps.notifications.services import notify_many

    reviewers = list(
        User.objects.filter(role__in=("admin", "reviewer"), is_active=True)
    )
    notify_many(
        users=reviewers,
        notification_type=NotificationType.APPROVAL_NEEDED,
        message=message,
        case=case,
        url=url,
    )


@transaction.atomic
def send_to_approval(entity, user) -> ApprovalFlow:
    """
    Создаёт новую запись ApprovalFlow (pending).
    Используется при первичном направлении и при повторном после RETURNED.
    """
    entity_type = _entity_type_for(entity)
    version = _next_version(entity_type, entity.id)

    flow = ApprovalFlow.objects.create(
        entity_type=entity_type,
        entity_id=entity.id,
        version=version,
        sent_by=user,
        result=ApprovalResult.PENDING,
    )

    audit_log(
        user=user,
        action="sent_to_approval",
        entity_type=entity_type,
        entity_id=entity.id,
        details={"version": version},
    )

    # Уведомляем reviewer/admin
    try:
        from django.urls import reverse
        case = getattr(entity, "case", None)
        case_num = case.case_number if case else str(entity.id)
        url = ""
        if case:
            url = reverse("approvals:queue")
        repeat = f" (повтор v{version})" if version > 1 else ""
        _notify_reviewers(
            message=(
                f"Требует согласования: {flow.get_entity_type_display()} "
                f"по делу {case_num}{repeat}."
            ),
            case=case,
            url=url,
        )
    except Exception:
        logger.exception("send_to_approval: failed to notify reviewers")

    logger.info(
        "ApprovalFlow created: entity_type=%s entity_id=%s version=%s by %s",
        entity_type, entity.id, version, user,
    )
    return flow


@transaction.atomic
def approve(flow: ApprovalFlow, reviewer, comment: str = "") -> ApprovalFlow:
    """Утверждает решение → вызывает on_approved на сущности."""
    if not flow.is_pending:
        raise ValueError("Согласование уже завершено.")

    flow.result = ApprovalResult.APPROVED
    flow.reviewed_by = reviewer
    flow.reviewed_at = timezone.now()
    flow.comment = comment
    flow.save(update_fields=["result", "reviewed_by", "reviewed_at", "comment"])

    _on_approved(flow, reviewer)

    audit_log(
        user=reviewer,
        action="approval_approved",
        entity_type=flow.entity_type,
        entity_id=flow.entity_id,
        details={"version": flow.version, "comment": comment},
    )

    # Уведомляем отправителя об утверждении
    try:
        from apps.notifications.models import NotificationType
        from apps.notifications.services import notify
        from django.urls import reverse

        sender = flow.sent_by
        if sender:
            case = _get_entity_case(flow)
            case_num = case.case_number if case else str(flow.entity_id)
            url = reverse("decisions:detail", kwargs={"pk": flow.entity_id}) if flow.entity_type == EntityType.DECISION else ""
            notify(
                user=sender,
                notification_type=NotificationType.STAGE_COMPLETED,
                message=f"Решение по делу {case_num} утверждено руководителем.",
                case=case,
                url=url,
            )
    except Exception:
        logger.exception("approve: failed to notify sender")

    logger.info(
        "ApprovalFlow approved: entity_type=%s entity_id=%s v%s by %s",
        flow.entity_type, flow.entity_id, flow.version, reviewer,
    )
    return flow


@transaction.atomic
def reject(flow: ApprovalFlow, reviewer, comment: str) -> ApprovalFlow:
    """Отклоняет решение."""
    if not flow.is_pending:
        raise ValueError("Согласование уже завершено.")
    if not comment.strip():
        raise ValueError("Комментарий при отклонении обязателен.")

    flow.result = ApprovalResult.REJECTED
    flow.reviewed_by = reviewer
    flow.reviewed_at = timezone.now()
    flow.comment = comment
    flow.save(update_fields=["result", "reviewed_by", "reviewed_at", "comment"])

    _on_rejected(flow, reviewer, comment)

    audit_log(
        user=reviewer,
        action="approval_rejected",
        entity_type=flow.entity_type,
        entity_id=flow.entity_id,
        details={"version": flow.version, "comment": comment},
    )

    # Уведомляем отправителя об отклонении
    try:
        from apps.notifications.models import NotificationType
        from apps.notifications.services import notify
        from django.urls import reverse

        sender = flow.sent_by
        if sender:
            case = _get_entity_case(flow)
            case_num = case.case_number if case else str(flow.entity_id)
            url = reverse("decisions:detail", kwargs={"pk": flow.entity_id}) if flow.entity_type == EntityType.DECISION else ""
            notify(
                user=sender,
                notification_type=NotificationType.RETURNED,
                message=f"Решение по делу {case_num} отклонено. Комментарий: {comment}",
                case=case,
                url=url,
            )
    except Exception:
        logger.exception("reject: failed to notify sender")

    logger.info(
        "ApprovalFlow rejected: entity_type=%s entity_id=%s v%s by %s",
        flow.entity_type, flow.entity_id, flow.version, reviewer,
    )
    return flow


@transaction.atomic
def return_for_revision(flow: ApprovalFlow, reviewer, comment: str) -> ApprovalFlow:
    """
    Возвращает на доработку: result=RETURNED, откатывает статус сущности.
    Оператор затем создаёт новую итерацию через send_to_approval().
    """
    if not flow.is_pending:
        raise ValueError("Согласование уже завершено.")
    if not comment.strip():
        raise ValueError("Комментарий при возврате обязателен.")

    flow.result = ApprovalResult.RETURNED
    flow.reviewed_by = reviewer
    flow.reviewed_at = timezone.now()
    flow.comment = comment
    flow.save(update_fields=["result", "reviewed_by", "reviewed_at", "comment"])

    _on_returned(flow, reviewer, comment)

    audit_log(
        user=reviewer,
        action="approval_returned",
        entity_type=flow.entity_type,
        entity_id=flow.entity_id,
        details={"version": flow.version, "comment": comment},
    )

    # Уведомляем отправителя о возврате
    try:
        from apps.notifications.models import NotificationType
        from apps.notifications.services import notify
        from django.urls import reverse

        sender = flow.sent_by
        if sender:
            case = _get_entity_case(flow)
            case_num = case.case_number if case else str(flow.entity_id)
            url = reverse("decisions:detail", kwargs={"pk": flow.entity_id}) if flow.entity_type == EntityType.DECISION else ""
            notify(
                user=sender,
                notification_type=NotificationType.RETURNED,
                message=(
                    f"Решение по делу {case_num} возвращено на доработку. "
                    f"Комментарий: {comment}"
                ),
                case=case,
                url=url,
            )
    except Exception:
        logger.exception("return_for_revision: failed to notify sender")

    logger.info(
        "ApprovalFlow returned: entity_type=%s entity_id=%s v%s by %s",
        flow.entity_type, flow.entity_id, flow.version, reviewer,
    )
    return flow


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def _get_entity_case(flow: ApprovalFlow):
    """Возвращает AdministrativeCase, связанный с сущностью flow."""
    try:
        if flow.entity_type == EntityType.DECISION:
            from apps.decisions.models import FinalDecision
            return FinalDecision.objects.select_related("case").get(pk=flow.entity_id).case
    except Exception:
        pass
    return None


# ─── Обработчики по типу сущности ─────────────────────────────────────────────

def _on_approved(flow: ApprovalFlow, reviewer):
    from apps.decisions.models import FinalDecision, DecisionStatus
    from apps.decisions.services import approve_decision

    if flow.entity_type == EntityType.DECISION:
        decision = FinalDecision.objects.get(pk=flow.entity_id)
        if decision.status == DecisionStatus.PENDING_APPROVAL:
            approve_decision(decision, reviewer)


def _on_rejected(flow: ApprovalFlow, reviewer, comment: str):
    from apps.decisions.models import FinalDecision, DecisionStatus
    from apps.decisions.services import reject_decision

    if flow.entity_type == EntityType.DECISION:
        decision = FinalDecision.objects.get(pk=flow.entity_id)
        if decision.status == DecisionStatus.PENDING_APPROVAL:
            reject_decision(decision, reviewer, comment)


def _on_returned(flow: ApprovalFlow, reviewer, comment: str):
    """
    RETURNED: откатывает статус дела к PROTOCOL_CREATED чтобы оператор
    мог создать новое решение и переотправить на согласование.
    """
    from apps.decisions.models import FinalDecision, DecisionStatus
    from apps.cases.models import CaseStatus, CaseEvent, CaseEventType
    from apps.cases.services import change_case_status

    if flow.entity_type == EntityType.DECISION:
        decision = FinalDecision.objects.select_related("case").get(pk=flow.entity_id)

        decision.status = DecisionStatus.REJECTED
        decision.rejection_comment = comment
        decision.approver = reviewer
        decision.save(update_fields=["status", "rejection_comment", "approver"])

        CaseEvent.objects.create(
            case=decision.case,
            event_type=CaseEventType.STATUS_CHANGED,
            description=(
                f"Решение возвращено на доработку. "
                f"Рецензент: {reviewer.get_full_name() or reviewer.username}. "
                f"Комментарий: {comment}"
            ),
            created_by=reviewer,
        )

        change_case_status(
            decision.case,
            CaseStatus.PROTOCOL_CREATED,
            reviewer,
            comment=f"Возврат на доработку: {comment}",
        )
