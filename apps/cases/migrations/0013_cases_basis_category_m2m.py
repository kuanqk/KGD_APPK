from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0012_taxauthoritydetails_refactor"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="administrativecase",
            name="basis",
        ),
        migrations.RemoveField(
            model_name="administrativecase",
            name="category",
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="basis",
            field=models.ManyToManyField(
                blank=True,
                related_name="cases",
                to="cases.CaseBasis",
                verbose_name="Основание",
            ),
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="category",
            field=models.ManyToManyField(
                blank=True,
                related_name="cases",
                to="cases.CaseCategory",
                verbose_name="Категория",
            ),
        ),
    ]
