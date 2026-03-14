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
            name="ApprovalFlow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_type", models.CharField(
                    choices=[
                        ("decision", "Итоговое решение"),
                        ("document", "Документ"),
                        ("case", "Дело"),
                    ],
                    db_index=True,
                    max_length=20,
                    verbose_name="Тип сущности",
                )),
                ("entity_id", models.PositiveIntegerField(db_index=True, verbose_name="ID сущности")),
                ("version", models.PositiveSmallIntegerField(default=1, verbose_name="Итерация согласования")),
                ("sent_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата направления")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата рассмотрения")),
                ("result", models.CharField(
                    choices=[
                        ("pending", "На согласовании"),
                        ("approved", "Утверждено"),
                        ("rejected", "Отклонено"),
                        ("returned", "Возвращено на доработку"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=20,
                    verbose_name="Результат",
                )),
                ("comment", models.TextField(blank=True, verbose_name="Комментарий рецензента")),
                ("reviewed_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="reviewed_approvals",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Рассмотрел",
                )),
                ("sent_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="sent_approvals",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Направил",
                )),
            ],
            options={
                "verbose_name": "Лист согласования",
                "verbose_name_plural": "Листы согласования",
                "ordering": ["-sent_at"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalflow",
            index=models.Index(fields=["entity_type", "entity_id"], name="approvals_entity_idx"),
        ),
    ]
