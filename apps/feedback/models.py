from django.db import models
from django.conf import settings


class FeedbackType(models.TextChoices):
    BUG = "bug", "Ошибка"
    SUGGESTION = "suggestion", "Предложение"
    QUESTION = "question", "Вопрос"


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
