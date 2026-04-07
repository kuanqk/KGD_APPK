from django.db import models
from django.conf import settings
from django.utils import timezone


class FeedbackType(models.TextChoices):
    BUG = "bug", "Ошибка"
    SUGGESTION = "suggestion", "Предложение"
    QUESTION = "question", "Вопрос"


class FeedbackStatus(models.TextChoices):
    NEW = "new", "Новое"
    IN_PROGRESS = "in_progress", "В работе"
    RESOLVED = "resolved", "Исправлено"
    REJECTED = "rejected", "Отклонено"


class FeedbackPriority(models.TextChoices):
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"
    CRITICAL = "critical", "Критический"


class Feedback(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="feedbacks",
        verbose_name="Пользователь",
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FeedbackType.choices,
        verbose_name="Тип",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.NEW,
        verbose_name="Статус",
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=FeedbackPriority.choices,
        default=FeedbackPriority.MEDIUM,
        verbose_name="Приоритет",
        db_index=True,
    )
    description = models.TextField(verbose_name="Описание")
    case_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Номер дела",
    )
    attachment = models.FileField(
        upload_to="feedback/",
        null=True,
        blank=True,
        verbose_name="Вложение",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата закрытия",
    )
    is_reviewed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Рассмотрено",
    )
    admin_comment = models.TextField(blank=True, verbose_name="Комментарий администратора")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_feedback_type_display()} от {self.user} — {self.created_at:%d.%m.%Y}"

    def resolve(self):
        """Перевести в статус Исправлено и проставить дату."""
        self.status = FeedbackStatus.RESOLVED
        self.is_reviewed = True
        self.resolved_at = timezone.now()

    @property
    def is_open(self):
        return self.status in (FeedbackStatus.NEW, FeedbackStatus.IN_PROGRESS)
