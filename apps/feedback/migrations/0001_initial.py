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
            name="Feedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("feedback_type", models.CharField(
                    choices=[("bug", "Ошибка"), ("suggestion", "Предложение"), ("question", "Вопрос")],
                    db_index=True,
                    max_length=20,
                    verbose_name="Тип",
                )),
                ("description", models.TextField(verbose_name="Описание")),
                ("case_number", models.CharField(blank=True, max_length=50, verbose_name="Номер дела")),
                ("attachment", models.FileField(blank=True, null=True, upload_to="feedback/", verbose_name="Вложение")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата")),
                ("is_reviewed", models.BooleanField(db_index=True, default=False, verbose_name="Рассмотрено")),
                ("admin_comment", models.TextField(blank=True, verbose_name="Комментарий администратора")),
                ("user", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="feedbacks",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Пользователь",
                )),
            ],
            options={
                "verbose_name": "Отзыв",
                "verbose_name_plural": "Отзывы",
                "ordering": ["-created_at"],
            },
        ),
    ]
