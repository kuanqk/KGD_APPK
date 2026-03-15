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
            name="DocumentTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("doc_type", models.CharField(
                    choices=[
                        ("notice", "Извещение о явке"),
                        ("preliminary_decision", "Предварительное решение"),
                        ("inspection_act", "Акт налогового обследования"),
                        ("der_request", "Запрос в ДЭР"),
                        ("hearing_protocol", "Протокол заслушивания"),
                        ("termination_decision", "Решение о прекращении"),
                        ("audit_initiation", "Инициирование внеплановой проверки"),
                        ("audit_order", "Приказ о назначении проверки"),
                    ],
                    db_index=True,
                    max_length=30,
                    verbose_name="Тип документа",
                )),
                ("name", models.CharField(max_length=200, verbose_name="Название шаблона")),
                ("body_template", models.TextField(
                    help_text="Django template syntax. Доступные переменные: case_number, taxpayer_name, taxpayer_iin, date_today, и др.",
                    verbose_name="Тело шаблона",
                )),
                ("version", models.PositiveIntegerField(default=1, verbose_name="Версия")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Активен")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_templates",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Создал",
                )),
            ],
            options={
                "verbose_name": "Шаблон документа",
                "verbose_name_plural": "Шаблоны документов",
                "ordering": ["doc_type", "-version"],
            },
        ),
        migrations.CreateModel(
            name="CaseDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("doc_type", models.CharField(
                    choices=[
                        ("notice", "Извещение о явке"),
                        ("preliminary_decision", "Предварительное решение"),
                        ("inspection_act", "Акт налогового обследования"),
                        ("der_request", "Запрос в ДЭР"),
                        ("hearing_protocol", "Протокол заслушивания"),
                        ("termination_decision", "Решение о прекращении"),
                        ("audit_initiation", "Инициирование внеплановой проверки"),
                        ("audit_order", "Приказ о назначении проверки"),
                    ],
                    db_index=True,
                    max_length=30,
                    verbose_name="Тип документа",
                )),
                ("doc_number", models.CharField(db_index=True, max_length=50, unique=True, verbose_name="Номер документа")),
                ("version", models.PositiveIntegerField(default=1, verbose_name="Версия")),
                ("status", models.CharField(
                    choices=[
                        ("draft", "Черновик"),
                        ("generated", "Сформирован"),
                        ("signed", "Подписан"),
                        ("cancelled", "Отменён"),
                    ],
                    db_index=True,
                    default="draft",
                    max_length=20,
                    verbose_name="Статус",
                )),
                ("file_path", models.CharField(blank=True, max_length=500, verbose_name="Путь к файлу")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")),
                ("metadata", models.JSONField(blank=True, default=dict, verbose_name="Метаданные")),
                ("case", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="documents",
                    to="cases.administrativecase",
                    verbose_name="Дело",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_documents",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Создал",
                )),
                ("template", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="generated_documents",
                    to="documents.documenttemplate",
                    verbose_name="Шаблон",
                )),
            ],
            options={
                "verbose_name": "Документ дела",
                "verbose_name_plural": "Документы дела",
                "ordering": ["-created_at"],
            },
        ),
    ]
