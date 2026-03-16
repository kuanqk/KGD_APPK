from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0007_administrativecase_case_number_max_length"),
    ]

    operations = [
        # ── Новые справочные модели ───────────────────────────────────────────
        migrations.CreateModel(
            name="Region",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=10, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=200, verbose_name="Наименование")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Активен")),
            ],
            options={"verbose_name": "Регион", "verbose_name_plural": "Регионы", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="CaseCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=200, verbose_name="Наименование")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Активна")),
            ],
            options={"verbose_name": "Категория дела", "verbose_name_plural": "Категории дел", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="CaseBasis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="Код")),
                ("name", models.CharField(max_length=200, verbose_name="Наименование")),
                ("legal_ref", models.TextField(blank=True, verbose_name="Ссылка на НПА")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Активно")),
            ],
            options={"verbose_name": "Основание дела", "verbose_name_plural": "Основания дел", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Position",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200, unique=True, verbose_name="Наименование")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Активна")),
            ],
            options={"verbose_name": "Должность", "verbose_name_plural": "Должности", "ordering": ["name"]},
        ),
        # ── Обновление AdministrativeCase ─────────────────────────────────────
        migrations.RemoveField(model_name="administrativecase", name="region"),
        migrations.AddField(
            model_name="administrativecase",
            name="region",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cases", to="cases.region",
                verbose_name="Регион", db_index=True,
            ),
        ),
        migrations.RemoveField(model_name="administrativecase", name="basis"),
        migrations.AddField(
            model_name="administrativecase",
            name="basis",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cases", to="cases.casebasis",
                verbose_name="Основание",
            ),
        ),
        migrations.RemoveField(model_name="administrativecase", name="category"),
        migrations.AddField(
            model_name="administrativecase",
            name="category",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cases", to="cases.casecategory",
                verbose_name="Категория",
            ),
        ),
    ]
