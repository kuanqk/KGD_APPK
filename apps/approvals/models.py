import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class ApprovalResult(models.TextChoices):
    PENDING = "pending", "На согласовании"
    APPROVED = "approved", "Утверждено"
    REJECTED = "rejected", "Отклонено"
    RETURNED = "returned", "Возвращено на доработку"


class EntityType(models.TextChoices):
    DECISION = "decision", "Итоговое решение"
    DOCUMENT = "document", "Документ"
    CASE = "case", "Дело"


class ApprovalFlowQuerySet(models.QuerySet):
    def for_entity(self, entity_type: str, entity_id: int):
        return self.filter(entity_type=entity_type, entity_id=entity_id).order_by("version")

    def pending(self):
        return self.filter(result=ApprovalResult.PENDING)

    def for_reviewer(self, user):
        """Reviewer видит все pending; operator видит только свои."""
        if user.role in ("admin", "reviewer"):
            return self.pending()
        return self.pending().filter(sent_by=user)


class ApprovalFlow(models.Model):
    entity_type = models.CharField(
        max_length=20,
        choices=EntityType.choices,
        verbose_name="Тип сущности",
        db_index=True,
    )
    entity_id = models.PositiveIntegerField(
        verbose_name="ID сущности",
        db_index=True,
    )
    version = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Итерация согласования",
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_approvals",
        verbose_name="Направил",
    )
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата направления",
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_approvals",
        verbose_name="Рассмотрел",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата рассмотрения",
    )
    result = models.CharField(
        max_length=20,
        choices=ApprovalResult.choices,
        default=ApprovalResult.PENDING,
        verbose_name="Результат",
        db_index=True,
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий рецензента",
    )

    objects = ApprovalFlowQuerySet.as_manager()

    class Meta:
        verbose_name = "Лист согласования"
        verbose_name_plural = "Листы согласования"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return (
            f"{self.get_entity_type_display()} #{self.entity_id} "
            f"v{self.version} [{self.get_result_display()}]"
        )

    @property
    def is_pending(self):
        return self.result == ApprovalResult.PENDING
