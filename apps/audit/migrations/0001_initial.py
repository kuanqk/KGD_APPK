from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(db_index=True, max_length=100, verbose_name="Действие")),
                ("entity_type", models.CharField(db_index=True, max_length=100, verbose_name="Тип объекта")),
                ("entity_id", models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name="ID объекта")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="Детали")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="IP-адрес")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата и время")),
                ("user", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="audit_logs",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Пользователь",
                )),
            ],
            options={
                "verbose_name": "Запись аудита",
                "verbose_name_plural": "Записи аудита",
                "ordering": ["-created_at"],
            },
        ),
    ]
