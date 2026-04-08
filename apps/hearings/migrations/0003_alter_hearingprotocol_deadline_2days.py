from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hearings", "0002_hearings_add_protocol_files"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hearingprotocol",
            name="deadline_2days",
            field=models.DateField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="Крайний срок (3 рабочих дня на замечания к протоколу, п. 6 ст. 74 АППК)",
            ),
        ),
    ]
