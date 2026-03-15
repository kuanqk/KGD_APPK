import logging
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.cases.models import Department

logger = logging.getLogger(__name__)


class UserRole(models.TextChoices):
    ADMIN = "admin", "Администратор"
    OPERATOR = "operator", "Оператор"
    REVIEWER = "reviewer", "Руководитель"
    EXECUTOR = "executor", "Исполнитель"
    OBSERVER = "observer", "Наблюдатель"


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.OPERATOR,
        verbose_name="Роль",
        db_index=True,
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Регион",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Телефон",
    )
    position = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Должность",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Подразделение",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_operator(self):
        return self.role == UserRole.OPERATOR

    @property
    def is_reviewer(self):
        return self.role == UserRole.REVIEWER

    @property
    def is_executor(self):
        return self.role == UserRole.EXECUTOR

    @property
    def is_observer(self):
        return self.role == UserRole.OBSERVER
