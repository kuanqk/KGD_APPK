import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class NotificationType(models.TextChoices):
    ASSIGNED = "assigned", "Назначено на вас"
    DEADLINE_SOON = "deadline_soon", "Дедлайн завтра"
    OVERDUE = "overdue", "Просрочено"
    RETURNED = "returned", "Возвращено на доработку"
    APPROVAL_NEEDED = "approval_needed", "Требует согласования"
    STAGE_COMPLETED = "stage_completed", "Этап завершён"


class NotificationQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(is_read=False)

    def for_user(self, user):
        return self.filter(user=user)


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Получатель",
    )
    case = models.ForeignKey(
        "cases.AdministrativeCase",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="Дело",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name="Тип",
        db_index=True,
    )
    message = models.TextField(verbose_name="Сообщение")
    url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Ссылка",
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name="Прочитано",
        db_index=True,
    )
    email_sent = models.BooleanField(
        default=False,
        verbose_name="Email отправлен",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        db_index=True,
    )

    objects = NotificationQuerySet.as_manager()

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.user} — {self.message[:60]}"
