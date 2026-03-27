import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class HearingFormat(models.TextChoices):
    IN_PERSON = "in_person", "Очно"
    REMOTE = "remote", "Дистанционно"
    MIXED = "mixed", "Смешанный формат"


class HearingStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Назначено"
    IN_PROGRESS = "in_progress", "Проводится"
    COMPLETED = "completed", "Проведено"
    CANCELLED = "cancelled", "Отменено"


class HearingQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.cases.models import AdministrativeCase
        allowed_cases = AdministrativeCase.objects.for_user(user)
        return self.filter(case__in=allowed_cases)

    def upcoming(self):
        from django.utils import timezone
        return self.filter(
            status=HearingStatus.SCHEDULED,
            hearing_date__gte=timezone.now().date(),
        ).order_by("hearing_date", "hearing_time")


class Hearing(models.Model):
    case = models.ForeignKey(
        "cases.AdministrativeCase",
        on_delete=models.PROTECT,
        related_name="hearings",
        verbose_name="Дело",
    )
    hearing_date = models.DateField(verbose_name="Дата заслушивания", db_index=True)
    hearing_time = models.TimeField(verbose_name="Время", null=True, blank=True)
    location = models.CharField(max_length=300, verbose_name="Место проведения")
    format = models.CharField(
        max_length=20,
        choices=HearingFormat.choices,
        default=HearingFormat.IN_PERSON,
        verbose_name="Формат",
    )
    status = models.CharField(
        max_length=20,
        choices=HearingStatus.choices,
        default=HearingStatus.SCHEDULED,
        verbose_name="Статус",
        db_index=True,
    )
    participants = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Участники",
        help_text='Список строк: ["ФИО, должность", ...]',
    )
    notes = models.TextField(blank=True, verbose_name="Примечания")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="scheduled_hearings",
        verbose_name="Назначил",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    objects = HearingQuerySet.as_manager()

    class Meta:
        verbose_name = "Заслушивание"
        verbose_name_plural = "Заслушивания"
        ordering = ["-hearing_date", "-hearing_time"]

    def __str__(self):
        return f"{self.case.case_number} | {self.hearing_date:%d.%m.%Y} | {self.get_status_display()}"

    @property
    def has_protocol(self):
        return hasattr(self, "protocol")


class HearingProtocol(models.Model):
    case = models.ForeignKey(
        "cases.AdministrativeCase",
        on_delete=models.PROTECT,
        related_name="protocols",
        verbose_name="Дело",
    )
    hearing = models.OneToOneField(
        Hearing,
        on_delete=models.PROTECT,
        related_name="protocol",
        verbose_name="Заслушивание",
    )
    protocol_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер протокола",
        db_index=True,
    )
    protocol_date = models.DateField(verbose_name="Дата протокола")
    result_summary = models.TextField(verbose_name="Краткое содержание / итог")
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Путь к файлу протокола",
    )
    signed_protocol_file = models.FileField(
        null=True, blank=True,
        upload_to='hearings/protocols/%Y/%m/',
        verbose_name='Подписанный протокол',
    )
    identity_doc_file = models.FileField(
        null=True, blank=True,
        upload_to='hearings/protocols/%Y/%m/',
        verbose_name='Удостоверение личности',
    )
    power_of_attorney_file = models.FileField(
        null=True, blank=True,
        upload_to='hearings/protocols/%Y/%m/',
        verbose_name='Доверенность',
    )
    deadline_2days = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дедлайн (2 рабочих дня)",
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_protocols",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Протокол заслушивания"
        verbose_name_plural = "Протоколы заслушивания"
        ordering = ["-protocol_date"]

    def __str__(self):
        return f"Протокол {self.protocol_number} от {self.protocol_date:%d.%m.%Y}"

    @property
    def is_deadline_overdue(self):
        from django.utils import timezone
        if self.deadline_2days:
            return timezone.now().date() > self.deadline_2days
        return False

    @property
    def days_until_deadline(self):
        from django.utils import timezone
        if self.deadline_2days:
            return (self.deadline_2days - timezone.now().date()).days
        return None
