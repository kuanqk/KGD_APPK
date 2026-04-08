import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class Department(models.Model):
    name = models.CharField(max_length=200, verbose_name="Наименование")
    code = models.CharField(
        max_length=2,
        unique=True,
        verbose_name="Код офиса (01-20)",
    )
    doc_sequence = models.PositiveIntegerField(default=0, verbose_name="Счётчик документов")
    seq_year = models.IntegerField(default=0, verbose_name="Год счётчика документов")
    case_sequence = models.PositiveIntegerField(default=0, verbose_name="Счётчик дел")
    case_seq_year = models.IntegerField(default=0, verbose_name="Год счётчика дел")

    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


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
    TERMINATION_PENDING = "termination_pending", "Решение о прекращении на согласовании"
    TERMINATED = "terminated", "Прекращено"
    AUDIT_PENDING = "audit_pending", "Инициирование проверки на согласовании"
    AUDIT_APPROVED = "audit_approved", "Проверка назначена"
    COMPLETED = "completed", "Завершено"
    ARCHIVED = "archived", "Архив"


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
        if user.role in ("admin", "reviewer"):
            return self
        if user.role == "executor":
            # Видит свои дела + дела где назначен наблюдателем
            return self.filter(
                models.Q(responsible_user=user) | models.Q(case_observers=user)
            ).distinct()
        # operator, observer — фильтр по офису + дела где назначен наблюдателем
        if user.department_id:
            return self.filter(
                models.Q(department=user.department) | models.Q(case_observers=user)
            ).distinct()
        if user.region:
            return self.filter(
                models.Q(region__name=user.region) | models.Q(case_observers=user)
            ).distinct()
        # Если нет офиса/региона — только дела где наблюдатель
        return self.filter(case_observers=user).distinct()


class AdministrativeCase(models.Model):
    case_number = models.CharField(
        max_length=30,
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
    region = models.ForeignKey(
        "Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        verbose_name="Регион",
        db_index=True,
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cases",
        verbose_name="Подразделение",
    )
    responsible_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_cases",
        verbose_name="Ответственный",
    )
    case_observers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="observed_cases",
        verbose_name="Наблюдатели",
        help_text="Могут просматривать дело и документы, но не создавать новые",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_cases",
        verbose_name="Создал",
    )
    basis = models.ManyToManyField(
        "CaseBasis",
        related_name="cases",
        verbose_name="Основание",
        blank=True,
    )
    category = models.ManyToManyField(
        "CaseCategory",
        related_name="cases",
        verbose_name="Категория",
        blank=True,
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата закрытия")

    # Контроль backdating
    allow_backdating = models.BooleanField(
        default=False,
        verbose_name="Разрешён ввод задним числом",
    )
    backdating_allowed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="backdating_approvals",
        verbose_name="Разрешил задним числом",
    )
    backdating_allowed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата разрешения задним числом",
    )
    backdating_comment = models.TextField(
        blank=True,
        verbose_name="Комментарий к вводу задним числом",
    )

    last_activity_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Последняя активность",
        db_index=True,
    )

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

    @property
    def basis_display(self):
        return ", ".join(b.name for b in self.basis.all())

    @property
    def category_display(self):
        return ", ".join(c.name for c in self.category.all())


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


class Region(models.Model):
    code = models.CharField(max_length=10, unique=True, verbose_name="Код")
    name = models.CharField(max_length=200, verbose_name="Наименование")
    is_active = models.BooleanField(default=True, verbose_name="Активен", db_index=True)

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CaseCategory(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Код")
    name = models.CharField(max_length=200, verbose_name="Наименование")
    is_active = models.BooleanField(default=True, verbose_name="Активна", db_index=True)

    class Meta:
        verbose_name = "Категория дела"
        verbose_name_plural = "Категории дел"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CaseBasis(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Код")
    name = models.CharField(max_length=200, verbose_name="Наименование")
    legal_ref = models.TextField(blank=True, verbose_name="Ссылка на НПА")
    is_active = models.BooleanField(default=True, verbose_name="Активно", db_index=True)

    class Meta:
        verbose_name = "Основание дела"
        verbose_name_plural = "Основания дел"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Наименование")
    is_active = models.BooleanField(default=True, verbose_name="Активна", db_index=True)

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"
        ordering = ["name"]

    def __str__(self):
        return self.name


class StagnationSettings(models.Model):
    """Singleton-настройки порога застывших дел (всегда pk=1)."""
    stagnation_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Порог застывания (дней)",
    )
    notify_reviewer = models.BooleanField(
        default=True,
        verbose_name="Уведомлять руководителя",
    )

    class Meta:
        verbose_name = "Настройки контроля застывших дел"
        verbose_name_plural = "Настройки контроля застывших дел"

    def __str__(self):
        return f"StagnationSettings(threshold={self.stagnation_days}d)"

    @classmethod
    def get(cls) -> "StagnationSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TaxAuthorityDetails(models.Model):
    """Реквизиты административного органа (КГД) — по одной записи на подразделение."""
    department = models.OneToOneField(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="authority_details",
        verbose_name="Подразделение",
    )
    region = models.ForeignKey(
        "Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_authority_details",
        verbose_name="Регион (если задан — дополнительный подбор реквизитов по делу)",
    )
    name = models.CharField(max_length=500, verbose_name="Наименование административного органа")
    bin_number = models.CharField(max_length=12, blank=True, verbose_name="БИН органа")
    address = models.TextField(blank=True, verbose_name="Адрес")
    city = models.CharField(max_length=200, blank=True, verbose_name="Город")
    phone = models.CharField(max_length=50, blank=True, verbose_name="Телефон")
    deputy_name = models.CharField(max_length=300, blank=True, verbose_name="ФИО заместителя")
    deputy_position = models.CharField(max_length=300, blank=True, verbose_name="Должность заместителя")
    is_active = models.BooleanField(default=True, verbose_name="Активна", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Кто изменил",
    )

    class Meta:
        verbose_name = "Реквизиты КГД"
        verbose_name_plural = "Реквизиты КГД"
        ordering = ["name"]

    def __str__(self):
        dept_str = f" ({self.department})" if self.department else ""
        return f"{self.name}{dept_str}" or "Реквизиты КГД"
