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
            name="Hearing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hearing_date", models.DateField(db_index=True, verbose_name="Дата заслушивания")),
                ("hearing_time", models.TimeField(blank=True, null=True, verbose_name="Время")),
                ("location", models.CharField(max_length=300, verbose_name="Место проведения")),
                ("format", models.CharField(
                    choices=[
                        ("in_person", "Очно"),
                        ("remote", "Дистанционно"),
                        ("mixed", "Смешанный формат"),
                    ],
                    default="in_person",
                    max_length=20,
                    verbose_name="Формат",
                )),
                ("status", models.CharField(
                    choices=[
                        ("scheduled", "Назначено"),
                        ("in_progress", "Проводится"),
                        ("completed", "Проведено"),
                        ("cancelled", "Отменено"),
                    ],
                    db_index=True,
                    default="scheduled",
                    max_length=20,
                    verbose_name="Статус",
                )),
                ("participants", models.JSONField(
                    blank=True,
                    default=list,
                    help_text='Список строк: ["ФИО, должность", ...]',
                    verbose_name="Участники",
                )),
                ("notes", models.TextField(blank=True, verbose_name="Примечания")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("case", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="hearings",
                    to="cases.administrativecase",
                    verbose_name="Дело",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="scheduled_hearings",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Назначил",
                )),
            ],
            options={
                "verbose_name": "Заслушивание",
                "verbose_name_plural": "Заслушивания",
                "ordering": ["-hearing_date", "-hearing_time"],
            },
        ),
        migrations.CreateModel(
            name="HearingProtocol",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("protocol_number", models.CharField(db_index=True, max_length=50, unique=True, verbose_name="Номер протокола")),
                ("protocol_date", models.DateField(verbose_name="Дата протокола")),
                ("result_summary", models.TextField(verbose_name="Краткое содержание / итог")),
                ("file_path", models.CharField(blank=True, max_length=500, verbose_name="Путь к файлу протокола")),
                ("deadline_2days", models.DateField(blank=True, db_index=True, null=True, verbose_name="Дедлайн (2 рабочих дня)")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("case", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="protocols",
                    to="cases.administrativecase",
                    verbose_name="Дело",
                )),
                ("hearing", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="protocol",
                    to="hearings.hearing",
                    verbose_name="Заслушивание",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_protocols",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Создал",
                )),
            ],
            options={
                "verbose_name": "Протокол заслушивания",
                "verbose_name_plural": "Протоколы заслушивания",
                "ordering": ["-protocol_date"],
            },
        ),
    ]
