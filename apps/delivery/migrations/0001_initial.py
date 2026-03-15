from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeliveryRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(
                    choices=[
                        ("in_person", "Нарочно"),
                        ("registered_mail", "Заказное письмо"),
                    ],
                    db_index=True,
                    max_length=20,
                    verbose_name="Способ вручения",
                )),
                ("status", models.CharField(
                    choices=[
                        ("pending", "Ожидается подтверждение"),
                        ("delivered", "Вручено"),
                        ("returned", "Возвращено"),
                    ],
                    db_index=True,
                    default="pending",
                    max_length=20,
                    verbose_name="Статус доставки",
                )),
                ("tracking_number", models.CharField(blank=True, db_index=True, max_length=100, verbose_name="Трек-номер")),
                ("sent_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата отправки")),
                ("delivered_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата вручения")),
                ("returned_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата возврата")),
                ("result", models.CharField(blank=True, max_length=200, verbose_name="Результат")),
                ("notes", models.TextField(blank=True, verbose_name="Примечание")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")),
                ("case_document", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="deliveries",
                    to="documents.casedocument",
                    verbose_name="Документ",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_deliveries",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="Создал",
                )),
            ],
            options={
                "verbose_name": "Запись о доставке",
                "verbose_name_plural": "Записи о доставке",
                "ordering": ["-created_at"],
            },
        ),
    ]
