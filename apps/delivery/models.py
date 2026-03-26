import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class DeliveryMethod(models.TextChoices):
    IN_PERSON = "in_person", "Нарочно"
    REGISTERED_MAIL = "registered_mail", "Заказное письмо"


class DeliveryStatus(models.TextChoices):
    PENDING = "pending", "Ожидается подтверждение"
    DELIVERED = "delivered", "Вручено"
    RETURNED = "returned", "Возвращено"


class DeliveryRecordQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.cases.models import AdministrativeCase
        allowed_cases = AdministrativeCase.objects.for_user(user)
        return self.filter(case_document__case__in=allowed_cases)

    def pending(self):
        return self.filter(status=DeliveryStatus.PENDING)


class DeliveryRecord(models.Model):
    case_document = models.ForeignKey(
        "documents.CaseDocument",
        on_delete=models.PROTECT,
        related_name="deliveries",
        verbose_name="Документ",
    )
    method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        verbose_name="Способ вручения",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        verbose_name="Статус доставки",
        db_index=True,
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Трек-номер",
        db_index=True,
    )
    sent_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Дата отправки",
    )
    delivered_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Дата вручения",
    )
    returned_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Дата возврата",
    )
    result = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Результат",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Примечание",
    )
    proof_file = models.FileField(
        null=True, blank=True,
        upload_to="delivery/proofs/%Y/%m/",
        verbose_name="Файл подтверждения",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_deliveries",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        db_index=True,
    )

    objects = DeliveryRecordQuerySet.as_manager()

    class Meta:
        verbose_name = "Запись о доставке"
        verbose_name_plural = "Записи о доставке"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.case_document.doc_number} | "
            f"{self.get_method_display()} | "
            f"{self.get_status_display()}"
        )

    @property
    def case(self):
        return self.case_document.case
