import logging
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Пользователь",
    )
    action = models.CharField(max_length=100, verbose_name="Действие", db_index=True)
    entity_type = models.CharField(max_length=100, verbose_name="Тип объекта", db_index=True)
    entity_id = models.BigIntegerField(null=True, blank=True, verbose_name="ID объекта", db_index=True)
    details = models.JSONField(default=dict, blank=True, verbose_name="Детали")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-адрес")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время", db_index=True)

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Записи аудита"
        ordering = ["-created_at"]

    def __str__(self):
        username = self.user.username if self.user else "анонимный"
        return f"{self.created_at:%d.%m.%Y %H:%M} | {username} | {self.action}"
