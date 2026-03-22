from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0010_alter_administrativecase_case_number_and_more"),
        ("cases", "0010_taxauthoritydetails"),
    ]

    operations = [
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="deputy_position",
            field=models.CharField(blank=True, max_length=300, verbose_name="Должность заместителя"),
        ),
    ]
