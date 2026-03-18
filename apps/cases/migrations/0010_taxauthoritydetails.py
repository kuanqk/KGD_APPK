from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0009_initial_data"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaxAuthorityDetails",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=500, verbose_name="Наименование административного органа")),
                ("address", models.TextField(verbose_name="Адрес")),
                ("deputy_name", models.CharField(max_length=300, verbose_name="ФИО заместителя")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Кто изменил",
                    ),
                ),
            ],
            options={
                "verbose_name": "Реквизиты КГД",
                "verbose_name_plural": "Реквизиты КГД",
            },
        ),
    ]
