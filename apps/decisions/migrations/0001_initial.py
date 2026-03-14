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
            name="FinalDecision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision_type", models.CharField(
                    choices=[("termination", "Прекращение дела"), ("tax_audit", "Назначение налоговой проверки")],
                    db_index=True,
                    max_length=20,
                    verbose_name="Тип решения",
                )),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Черновик"),
                        ("pending_approval", "На согласовании"),
                        ("approved", "Утверждено"),
                        ("rejected", "Отклонено"),
                    ],
                    db_index=True,
                    default="pending_approval",
                    max_length=20,
                    verbose_name="Статус согласования",
                )),
                ("basis", models.CharField(
                    blank=True,
                    choices=[
                        ("violation_not_confirmed", "Нарушение не подтверждено"),
                        ("violation_self_corrected", "Нарушение устранено самостоятельно"),
                    ],
                    max_length=50,
                    verbose_name="Основание прекращения",
                )),
                ("comment", models.TextField(verbose_name="Комментарий / обоснование")),
                ("decision_date", models.DateField(auto_now_add=True, verbose_name="Дата составления")),
                ("approved_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата согласования")),
                ("rejection_comment", models.TextField(blank=True, verbose_name="Комментарий при отклонении")),
                ("file_path", models.CharField(blank=True, max_length=500, verbose_name="Путь к файлу решения")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")),
                ("approver", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="approved_decisions",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Согласующий",
                )),
                ("case", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="final_decision",
                    to="cases.administrativecase",
                    verbose_name="Дело",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_decisions",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Создал",
                )),
                ("responsible", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="responsible_decisions",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Ответственный",
                )),
            ],
            options={
                "verbose_name": "Итоговое решение",
                "verbose_name_plural": "Итоговые решения",
                "ordering": ["-created_at"],
            },
        ),
    ]
