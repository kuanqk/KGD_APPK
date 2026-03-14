from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cases", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(
                    choices=[
                        ("assigned", "Назначено на вас"),
                        ("deadline_soon", "Дедлайн завтра"),
                        ("overdue", "Просрочено"),
                        ("returned", "Возвращено на доработку"),
                        ("approval_needed", "Требует согласования"),
                        ("stage_completed", "Этап завершён"),
                    ],
                    db_index=True,
                    max_length=30,
                    verbose_name="Тип",
                )),
                ("message", models.TextField(verbose_name="Сообщение")),
                ("url", models.CharField(blank=True, max_length=500, verbose_name="Ссылка")),
                ("is_read", models.BooleanField(db_index=True, default=False, verbose_name="Прочитано")),
                ("email_sent", models.BooleanField(default=False, verbose_name="Email отправлен")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")),
                ("case", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to="cases.administrativecase",
                    verbose_name="Дело",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Получатель",
                )),
            ],
            options={
                "verbose_name": "Уведомление",
                "verbose_name_plural": "Уведомления",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["user", "is_read"], name="notif_user_read_idx"),
        ),
    ]
