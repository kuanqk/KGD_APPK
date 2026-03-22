"""
Schema migration: расширяет TaxAuthorityDetails из singleton в справочник.
Добавляет поля: department (OneToOne FK), bin_number, city, phone, is_active.
Убирает ограничение singleton (get_singleton удалён из модели).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0011_taxauthoritydetails_deputy_position"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="department",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="authority_details",
                to="cases.department",
                verbose_name="Подразделение",
            ),
        ),
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="bin_number",
            field=models.CharField(blank=True, max_length=12, verbose_name="БИН органа"),
        ),
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="city",
            field=models.CharField(blank=True, max_length=200, verbose_name="Город"),
        ),
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="phone",
            field=models.CharField(blank=True, max_length=50, verbose_name="Телефон"),
        ),
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True, verbose_name="Активна"),
        ),
        migrations.AlterField(
            model_name="taxauthoritydetails",
            name="address",
            field=models.TextField(blank=True, verbose_name="Адрес"),
        ),
        migrations.AlterField(
            model_name="taxauthoritydetails",
            name="deputy_name",
            field=models.CharField(blank=True, max_length=300, verbose_name="ФИО заместителя"),
        ),
        migrations.AlterModelOptions(
            name="taxauthoritydetails",
            options={
                "ordering": ["name"],
                "verbose_name": "Реквизиты КГД",
                "verbose_name_plural": "Реквизиты КГД",
            },
        ),
    ]
