from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0002_administrativecase_backdating"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="Наименование")),
                ("code", models.CharField(max_length=2, unique=True, verbose_name="Код офиса (01-20)")),
                ("doc_sequence", models.PositiveIntegerField(default=0, verbose_name="Счётчик документов")),
                ("seq_year", models.IntegerField(default=0, verbose_name="Год счётчика")),
            ],
            options={
                "verbose_name": "Подразделение",
                "verbose_name_plural": "Подразделения",
                "ordering": ["code"],
            },
        ),
    ]
