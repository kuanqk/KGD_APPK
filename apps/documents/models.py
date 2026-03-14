import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class DocumentType(models.TextChoices):
    NOTICE = "notice", "Извещение о явке"
    PRELIMINARY_DECISION = "preliminary_decision", "Предварительное решение"
    INSPECTION_ACT = "inspection_act", "Акт налогового обследования"
    DER_REQUEST = "der_request", "Запрос в ДЭР"
    HEARING_PROTOCOL = "hearing_protocol", "Протокол заслушивания"
    TERMINATION_DECISION = "termination_decision", "Решение о прекращении"
    AUDIT_INITIATION = "audit_initiation", "Инициирование внеплановой проверки"
    AUDIT_ORDER = "audit_order", "Приказ о назначении проверки"


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    GENERATED = "generated", "Сформирован"
    SIGNED = "signed", "Подписан"
    CANCELLED = "cancelled", "Отменён"


class DocumentTemplate(models.Model):
    doc_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        verbose_name="Тип документа",
        db_index=True,
    )
    name = models.CharField(max_length=200, verbose_name="Название шаблона")
    body_template = models.TextField(
        verbose_name="Тело шаблона",
        help_text="Django template syntax. Доступные переменные: case_number, taxpayer_name, taxpayer_iin, date_today, и др.",
    )
    version = models.PositiveIntegerField(default=1, verbose_name="Версия")
    is_active = models.BooleanField(default=True, verbose_name="Активен", db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_templates",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Шаблон документа"
        verbose_name_plural = "Шаблоны документов"
        ordering = ["doc_type", "-version"]

    def __str__(self):
        return f"{self.get_doc_type_display()} v{self.version}"

    def save(self, *args, **kwargs):
        if self.is_active and self.pk is None:
            # Новый активный шаблон → деактивировать предыдущие того же типа
            DocumentTemplate.objects.filter(doc_type=self.doc_type, is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class CaseDocumentQuerySet(models.QuerySet):
    def for_user(self, user):
        from apps.cases.models import AdministrativeCase
        allowed_cases = AdministrativeCase.objects.for_user(user)
        return self.filter(case__in=allowed_cases)

    def active(self):
        return self.exclude(status=DocumentStatus.CANCELLED)


class CaseDocument(models.Model):
    case = models.ForeignKey(
        "cases.AdministrativeCase",
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name="Дело",
    )
    template = models.ForeignKey(
        DocumentTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
        verbose_name="Шаблон",
    )
    doc_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        verbose_name="Тип документа",
        db_index=True,
    )
    doc_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Номер документа",
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1, verbose_name="Версия")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
        verbose_name="Статус",
        db_index=True,
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Путь к файлу",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_documents",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания", db_index=True)
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Метаданные")

    objects = CaseDocumentQuerySet.as_manager()

    class Meta:
        verbose_name = "Документ дела"
        verbose_name_plural = "Документы дела"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.doc_number} — {self.get_doc_type_display()}"

    def delete(self, *args, **kwargs):
        if self.status == DocumentStatus.SIGNED:
            raise ValueError(
                f"Документ {self.doc_number} подписан — удаление запрещено. Создайте новую версию."
            )
        super().delete(*args, **kwargs)

    @property
    def is_deletable(self):
        return self.status != DocumentStatus.SIGNED

    @property
    def file_url(self):
        if self.file_path:
            from django.conf import settings as django_settings
            return f"{django_settings.MEDIA_URL}{self.file_path}"
        return None
