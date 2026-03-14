import logging
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.cases.models import CaseEvent, CaseEventType, CaseStatus
from apps.cases.services import change_case_status
from .models import DecisionStatus, DecisionType, FinalDecision, TerminationBasis

logger = logging.getLogger(__name__)


def _guard_protocol_required(case):
    """Жёсткое бизнес-правило: итоговое решение только при наличии протокола."""
    if case.status != CaseStatus.PROTOCOL_CREATED:
        raise PermissionDenied(
            f"Итоговое решение невозможно: статус дела «{case.get_status_display()}». "
            f"Требуется статус «{CaseStatus.PROTOCOL_CREATED.label}»."
        )
    if not case.protocols.exists():
        raise PermissionDenied(
            "Итоговое решение заблокировано: протокол заслушивания не оформлен."
        )


@transaction.atomic
def create_termination(
    case,
    basis: str,
    comment: str,
    user,
) -> FinalDecision:
    """
    Сценарий A: Решение о прекращении административного дела.
    Guard: статус дела PROTOCOL_CREATED + наличие протокола.
    Basis: только VIOLATION_NOT_CONFIRMED или VIOLATION_SELF_CORRECTED.
    """
    _guard_protocol_required(case)

    if basis not in TerminationBasis.values:
        raise ValueError(f"Недопустимое основание прекращения: {basis}")

    if hasattr(case, "final_decision"):
        raise ValueError("По данному делу уже существует итоговое решение.")

    decision = FinalDecision.objects.create(
        case=case,
        decision_type=DecisionType.TERMINATION,
        status=DecisionStatus.PENDING_APPROVAL,
        basis=basis,
        comment=comment,
        responsible=case.responsible_user,
        created_by=user,
    )

    # Генерируем PDF решения
    try:
        from apps.documents.models import DocumentType
        from apps.documents.services import generate_document
        doc = generate_document(case, DocumentType.TERMINATION_DECISION, user)
        decision.file_path = doc.file_path
        decision.save(update_fields=["file_path"])
    except ValueError as e:
        logger.warning("Termination PDF not generated: %s", e)

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.DECISION_MADE,
        description=(
            f"Решение о прекращении дела составлено. "
            f"Основание: {TerminationBasis(basis).label}. "
            f"Направлено на согласование."
        ),
        created_by=user,
    )

    change_case_status(case, CaseStatus.TERMINATION_PENDING, user)

    audit_log(
        user=user,
        action="termination_created",
        entity_type="decision",
        entity_id=decision.id,
        details={
            "case_number": case.case_number,
            "basis": basis,
        },
    )

    logger.info("Termination decision created for case %s by %s", case.case_number, user)
    return decision


@transaction.atomic
def create_tax_audit(
    case,
    comment: str,
    user,
) -> FinalDecision:
    """
    Сценарий B: Инициирование внеплановой налоговой проверки.
    Guard: статус дела PROTOCOL_CREATED + наличие протокола.
    """
    _guard_protocol_required(case)

    if hasattr(case, "final_decision"):
        raise ValueError("По данному делу уже существует итоговое решение.")

    decision = FinalDecision.objects.create(
        case=case,
        decision_type=DecisionType.TAX_AUDIT,
        status=DecisionStatus.PENDING_APPROVAL,
        comment=comment,
        responsible=case.responsible_user,
        created_by=user,
    )

    # Генерируем PDF инициирования проверки
    try:
        from apps.documents.models import DocumentType
        from apps.documents.services import generate_document
        doc = generate_document(case, DocumentType.AUDIT_INITIATION, user)
        decision.file_path = doc.file_path
        decision.save(update_fields=["file_path"])
    except ValueError as e:
        logger.warning("Tax audit PDF not generated: %s", e)

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.DECISION_MADE,
        description="Инициирование внеплановой проверки. Направлено на согласование.",
        created_by=user,
    )

    change_case_status(case, CaseStatus.AUDIT_PENDING, user)

    audit_log(
        user=user,
        action="tax_audit_created",
        entity_type="decision",
        entity_id=decision.id,
        details={"case_number": case.case_number},
    )

    logger.info("Tax audit decision created for case %s by %s", case.case_number, user)
    return decision


@transaction.atomic
def approve_decision(decision: FinalDecision, approver) -> FinalDecision:
    """Руководитель утверждает решение → финальный статус дела."""
    if decision.status != DecisionStatus.PENDING_APPROVAL:
        raise ValueError("Решение не находится на согласовании.")

    decision.status = DecisionStatus.APPROVED
    decision.approver = approver
    decision.approved_at = timezone.now()
    decision.save(update_fields=["status", "approver", "approved_at"])

    case = decision.case
    if decision.is_termination:
        final_case_status = CaseStatus.TERMINATED
        event_desc = "Решение о прекращении дела утверждено руководителем."
        # Генерируем приказ о прекращении если ещё не было
        try:
            from apps.documents.models import DocumentType
            from apps.documents.services import generate_document
            generate_document(case, DocumentType.AUDIT_ORDER, approver)
        except ValueError:
            pass
    else:
        final_case_status = CaseStatus.AUDIT_APPROVED
        event_desc = "Решение о назначении проверки утверждено руководителем."

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.DECISION_MADE,
        description=event_desc,
        created_by=approver,
    )

    change_case_status(case, final_case_status, approver)

    audit_log(
        user=approver,
        action="decision_approved",
        entity_type="decision",
        entity_id=decision.id,
        details={
            "case_number": case.case_number,
            "decision_type": decision.decision_type,
            "final_status": final_case_status,
        },
    )

    logger.info("Decision %s approved by %s → case %s", decision.id, approver, final_case_status)
    return decision


@transaction.atomic
def reject_decision(
    decision: FinalDecision,
    approver,
    rejection_comment: str,
) -> FinalDecision:
    """Руководитель отклоняет решение → дело возвращается в PROTOCOL_CREATED."""
    if decision.status != DecisionStatus.PENDING_APPROVAL:
        raise ValueError("Решение не находится на согласовании.")

    if not rejection_comment.strip():
        raise ValueError("Комментарий при отклонении обязателен.")

    decision.status = DecisionStatus.REJECTED
    decision.approver = approver
    decision.approved_at = timezone.now()
    decision.rejection_comment = rejection_comment
    decision.save(update_fields=["status", "approver", "approved_at", "rejection_comment"])

    case = decision.case

    CaseEvent.objects.create(
        case=case,
        event_type=CaseEventType.STATUS_CHANGED,
        description=f"Решение отклонено руководителем. Комментарий: {rejection_comment}",
        created_by=approver,
    )

    # Откатываем дело в PROTOCOL_CREATED — оператор создаёт новое решение
    change_case_status(case, CaseStatus.PROTOCOL_CREATED, approver,
                       comment=f"Решение отклонено: {rejection_comment}")

    audit_log(
        user=approver,
        action="decision_rejected",
        entity_type="decision",
        entity_id=decision.id,
        details={
            "case_number": case.case_number,
            "rejection_comment": rejection_comment,
        },
    )

    logger.info("Decision %s rejected by %s", decision.id, approver)
    return decision


@transaction.atomic
def archive_case(case, user) -> None:
    """Переводит завершённое дело в архив."""
    if case.status not in (CaseStatus.TERMINATED, CaseStatus.AUDIT_APPROVED, CaseStatus.COMPLETED):
        raise ValueError("Архивировать можно только завершённые дела.")

    change_case_status(case, CaseStatus.ARCHIVED, user, comment="Дело переведено в архив")

    audit_log(
        user=user,
        action="case_archived",
        entity_type="case",
        entity_id=case.id,
        details={"case_number": case.case_number},
    )
