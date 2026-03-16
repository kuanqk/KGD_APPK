from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0004_administrativecase_department_fk"),
    ]

    operations = [
        migrations.CreateModel(
            name="StagnationSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stagnation_days", models.PositiveIntegerField(default=30, verbose_name="Порог застывания (дней)")),
                ("notify_reviewer", models.BooleanField(default=True, verbose_name="Уведомлять руководителя")),
            ],
            options={
                "verbose_name": "Настройки контроля застывших дел",
                "verbose_name_plural": "Настройки контроля застывших дел",
            },
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="last_activity_at",
            field=models.DateTimeField(
                auto_now_add=True,
                verbose_name="Последняя активность",
                db_index=True,
            ),
            preserve_default=False,
        ),
    ]
