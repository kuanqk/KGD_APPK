import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class TerminationBasis(models.TextChoices):
    VIOLATION_NOT_CONFIRMED = "violation_not_confirmed", "Нарушение не подтверждено"
    VIOLATION_SELF_CORRECTED = "violation_self_corrected", "Нарушение устранено самостоятельно"


class DecisionType(models.TextChoices):
    TERMINATION = "termination", "Прекращение дела"
    TAX_AUDIT = "tax_audit", "Назначение налоговой проверки"


class DecisionStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    PENDING_APPROVAL = "pending_approval", "На согласовании"
    APPROVED = "approved", "Утверждено"
    REJECTED = "rejected", "Отклонено"


class FinalDecisionQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.cases.models import AdministrativeCase
        allowed_cases = AdministrativeCase.objects.for_user(user)
        return self.filter(case__in=allowed_cases)

    def pending_approval(self):
        return self.filter(status=DecisionStatus.PENDING_APPROVAL)


class FinalDecision(models.Model):
    case = models.OneToOneField(
        "cases.AdministrativeCase",
        on_delete=models.PROTECT,
        related_name="final_decision",
        verbose_name="Дело",
    )
    decision_type = models.CharField(
        max_length=20,
        choices=DecisionType.choices,
        verbose_name="Тип решения",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=DecisionStatus.choices,
        default=DecisionStatus.PENDING_APPROVAL,
        verbose_name="Статус согласования",
        db_index=True,
    )
    basis = models.CharField(
        max_length=50,
        choices=TerminationBasis.choices,
        blank=True,
        verbose_name="Основание прекращения",
    )
    comment = models.TextField(verbose_name="Комментарий / обоснование")
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_decisions",
        verbose_name="Ответственный",
    )
    decision_date = models.DateField(
        auto_now_add=True,
        verbose_name="Дата составления",
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_decisions",
        verbose_name="Согласующий",
    )
    approved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Дата согласования",
    )
    rejection_comment = models.TextField(
        blank=True,
        verbose_name="Комментарий при отклонении",
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Путь к файлу решения",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_decisions",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        db_index=True,
    )

    objects = FinalDecisionQuerySet.as_manager()

    class Meta:
        verbose_name = "Итоговое решение"
        verbose_name_plural = "Итоговые решения"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_decision_type_display()} по делу {self.case.case_number} "
            f"[{self.get_status_display()}]"
        )

    @property
    def is_termination(self):
        return self.decision_type == DecisionType.TERMINATION

    @property
    def is_tax_audit(self):
        return self.decision_type == DecisionType.TAX_AUDIT

    @property
    def basis_display(self):
        return self.get_basis_display()
