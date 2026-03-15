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
            name="Taxpayer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("iin_bin", models.CharField(db_index=True, max_length=12, unique=True, verbose_name="ИИН/БИН")),
                ("name", models.CharField(max_length=500, verbose_name="Наименование / ФИО")),
                ("taxpayer_type", models.CharField(
                    choices=[
                        ("individual", "Физическое лицо"),
                        ("legal", "Юридическое лицо"),
                        ("ie", "Индивидуальный предприниматель"),
                    ],
                    default="legal",
                    max_length=20,
                    verbose_name="Тип налогоплательщика",
                )),
                ("address", models.TextField(blank=True, verbose_name="Адрес")),
                ("phone", models.CharField(blank=True, max_length=30, verbose_name="Телефон")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="Email")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")),
            ],
            options={
                "verbose_name": "Налогоплательщик",
                "verbose_name_plural": "Налогоплательщики",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="AdministrativeCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("case_number", models.CharField(db_index=True, max_length=20, unique=True, verbose_name="Номер дела")),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Черновик"),
                        ("notice_created", "Извещение создано"),
                        ("notice_sent", "Извещение направлено"),
                        ("delivered", "Вручено"),
                        ("returned", "Возврат"),
                        ("mail_returned", "Возврат почтового отправления"),
                        ("act_created", "Акт обследования оформлен"),
                        ("der_sent", "Запрос в ДЭР направлен"),
                        ("hearing_scheduled", "Заслушивание назначено"),
                        ("hearing_done", "Заслушивание проведено"),
                        ("protocol_created", "Протокол оформлен"),
                        ("termination_pending", "Решение о прекращении на согласовании"),
                        ("terminated", "Прекращено"),
                        ("audit_pending", "Инициирование проверки на согласовании"),
                        ("audit_approved", "Проверка назначена"),
                        ("completed", "Завершено"),
                        ("archived", "Архив"),
                    ],
                    db_index=True,
                    default="draft",
                    max_length=30,
                    verbose_name="Статус",
                )),
                ("region", models.CharField(db_index=True, max_length=100, verbose_name="Регион")),
                ("department", models.CharField(blank=True, max_length=200, verbose_name="Подразделение")),
                ("basis", models.CharField(
                    choices=[
                        ("tax_violation", "Налоговое нарушение"),
                        ("declaration_error", "Ошибка в декларации"),
                        ("unreported_income", "Незадекларированный доход"),
                        ("other", "Иное"),
                    ],
                    default="other",
                    max_length=30,
                    verbose_name="Основание",
                )),
                ("category", models.CharField(blank=True, max_length=200, verbose_name="Категория")),
                ("description", models.TextField(blank=True, verbose_name="Описание")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("closed_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата закрытия")),
                ("taxpayer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="cases",
                    to="cases.taxpayer",
                    verbose_name="Налогоплательщик",
                )),
                ("responsible_user", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="responsible_cases",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Ответственный",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_cases",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Создал",
                )),
            ],
            options={
                "verbose_name": "Административное дело",
                "verbose_name_plural": "Административные дела",
                "ordering": ["-created_at"],
                "permissions": [
                    ("can_change_status", "Может менять статус дела"),
                    ("can_assign_responsible", "Может назначать ответственного"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CaseEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(
                    choices=[
                        ("created", "Дело создано"),
                        ("status_changed", "Смена статуса"),
                        ("document_added", "Документ добавлен"),
                        ("comment_added", "Комментарий добавлен"),
                        ("assigned", "Назначен ответственный"),
                        ("hearing_scheduled", "Заслушивание назначено"),
                        ("decision_made", "Решение принято"),
                    ],
                    db_index=True,
                    max_length=30,
                    verbose_name="Тип события",
                )),
                ("description", models.TextField(verbose_name="Описание")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата и время")),
                ("case", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="cases.administrativecase",
                    verbose_name="Дело",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="case_events",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Автор",
                )),
            ],
            options={
                "verbose_name": "Событие дела",
                "verbose_name_plural": "События дела",
                "ordering": ["-created_at"],
            },
        ),
    ]
