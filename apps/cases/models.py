import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class TaxpayerType(models.TextChoices):
    INDIVIDUAL = "individual", "Физическое лицо"
    LEGAL = "legal", "Юридическое лицо"
    IE = "ie", "Индивидуальный предприниматель"


class CaseStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    NOTICE_CREATED = "notice_created", "Извещение создано"
    NOTICE_SENT = "notice_sent", "Извещение направлено"
    DELIVERED = "delivered", "Вручено"
    RETURNED = "returned", "Возврат"
    MAIL_RETURNED = "mail_returned", "Возврат почтового отправления"
    ACT_CREATED = "act_created", "Акт обследования оформлен"
    DER_SENT = "der_sent", "Запрос в ДЭР направлен"
    HEARING_SCHEDULED = "hearing_scheduled", "Заслушивание назначено"
    HEARING_DONE = "hearing_done", "Заслушивание проведено"
    PROTOCOL_CREATED = "protocol_created", "Протокол оформлен"
    DECISION_PENDING = "decision_pending", "Ожидает решения"
    TERMINATED = "terminated", "Прекращено"
    AUDIT_INITIATED = "audit_initiated", "Инициирована проверка"
    COMPLETED = "completed", "Завершено"
    ARCHIVED = "archived", "Архив"


class CaseBasis(models.TextChoices):
    TAX_VIOLATION = "tax_violation", "Налоговое нарушение"
    DECLARATION_ERROR = "declaration_error", "Ошибка в декларации"
    UNREPORTED_INCOME = "unreported_income", "Незадекларированный доход"
    OTHER = "other", "Иное"


class CaseEventType(models.TextChoices):
    CREATED = "created", "Дело создано"
    STATUS_CHANGED = "status_changed", "Смена статуса"
    DOCUMENT_ADDED = "document_added", "Документ добавлен"
    COMMENT_ADDED = "comment_added", "Комментарий добавлен"
    ASSIGNED = "assigned", "Назначен ответственный"
    HEARING_SCHEDULED = "hearing_scheduled", "Заслушивание назначено"
    DECISION_MADE = "decision_made", "Решение принято"


class TaxpayerQuerySet(models.QuerySet):
    pass


class Taxpayer(models.Model):
    iin_bin = models.CharField(
        max_length=12,
        unique=True,
        verbose_name="ИИН/БИН",
        db_index=True,
    )
    name = models.CharField(max_length=500, verbose_name="Наименование / ФИО")
    taxpayer_type = models.CharField(
        max_length=20,
        choices=TaxpayerType.choices,
        default=TaxpayerType.LEGAL,
        verbose_name="Тип налогоплательщика",
    )
    address = models.TextField(blank=True, verbose_name="Адрес")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    objects = TaxpayerQuerySet.as_manager()

    class Meta:
        verbose_name = "Налогоплательщик"
        verbose_name_plural = "Налогоплательщики"
        ordering = ["name"]

    def __str__(self):
        return f"{self.iin_bin} — {self.name}"


class CaseQuerySet(models.QuerySet):
    def for_user(self, user):
        if user.role == "observer":
            return self.filter(region=user.region)
        if user.role == "executor":
            return self.filter(responsible_user=user)
        return self  # admin, operator, reviewer — всё


class AdministrativeCase(models.Model):
    case_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Номер дела",
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=CaseStatus.choices,
        default=CaseStatus.DRAFT,
        verbose_name="Статус",
        db_index=True,
    )
    taxpayer = models.ForeignKey(
        Taxpayer,
        on_delete=models.PROTECT,
        related_name="cases",
        verbose_name="Налогоплательщик",
    )
    region = models.CharField(max_length=100, verbose_name="Регион", db_index=True)
    department = models.CharField(max_length=200, blank=True, verbose_name="Подразделение")
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_cases",
        verbose_name="Ответственный",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_cases",
        verbose_name="Создал",
    )
    basis = models.CharField(
        max_length=30,
        choices=CaseBasis.choices,
        default=CaseBasis.OTHER,
        verbose_name="Основание",
    )
    category = models.CharField(max_length=200, blank=True, verbose_name="Категория")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата закрытия")

    objects = CaseQuerySet.as_manager()

    class Meta:
        verbose_name = "Административное дело"
        verbose_name_plural = "Административные дела"
        ordering = ["-created_at"]
        permissions = [
            ("can_change_status", "Может менять статус дела"),
            ("can_assign_responsible", "Может назначать ответственного"),
        ]

    def __str__(self):
        return self.case_number


class CaseEvent(models.Model):
    case = models.ForeignKey(
        AdministrativeCase,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Дело",
    )
    event_type = models.CharField(
        max_length=30,
        choices=CaseEventType.choices,
        verbose_name="Тип события",
        db_index=True,
    )
    description = models.TextField(verbose_name="Описание")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="case_events",
        verbose_name="Автор",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время", db_index=True)

    class Meta:
        verbose_name = "Событие дела"
        verbose_name_plural = "События дела"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case.case_number} | {self.get_event_type_display()} | {self.created_at:%d.%m.%Y %H:%M}"
