from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0003_department"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="administrativecase",
            name="department",
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cases",
                to="cases.department",
                verbose_name="Подразделение",
            ),
        ),
    ]
