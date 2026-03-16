from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0006_department_case_sequence"),
    ]

    operations = [
        migrations.AlterField(
            model_name="administrativecase",
            name="case_number",
            field=models.CharField(max_length=30, unique=True, verbose_name="Номер дела"),
        ),
    ]
