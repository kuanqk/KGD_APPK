from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0005_stagnationsettings_last_activity_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="case_sequence",
            field=models.PositiveIntegerField(default=0, verbose_name="Счётчик дел"),
        ),
        migrations.AddField(
            model_name="department",
            name="case_seq_year",
            field=models.IntegerField(default=0, verbose_name="Год счётчика дел"),
        ),
    ]
