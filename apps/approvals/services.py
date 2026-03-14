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

    logger.info(
        "ApprovalFlow approved: entity_type=%s entity_id=%s v%s by %s",
        flow.entity_type, flow.entity_id, flow.version, reviewer,
    )
    return flow


@transaction.atomic
def reject(flow: ApprovalFlow, reviewer, comment: str) -> ApprovalFlow:
    """Отклоняет решение без возврата на доработку."""
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

    logger.info(
        "ApprovalFlow returned: entity_type=%s entity_id=%s v%s by %s",
        flow.entity_type, flow.entity_id, flow.version, reviewer,
    )
    return flow


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
    RETURNED: откатывает FinalDecision → PENDING_APPROVAL остаётся,
    но статус дела возвращается к PROTOCOL_CREATED чтобы оператор
    мог отредактировать и переотправить на согласование.
    """
    from apps.decisions.models import FinalDecision, DecisionStatus
    from apps.cases.models import CaseStatus, CaseEvent, CaseEventType
    from apps.cases.services import change_case_status

    if flow.entity_type == EntityType.DECISION:
        decision = FinalDecision.objects.select_related("case").get(pk=flow.entity_id)

        # Помечаем само решение как возвращённое (используем REJECTED в модели —
        # визуально отличаем через ApprovalFlow.result=RETURNED)
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
