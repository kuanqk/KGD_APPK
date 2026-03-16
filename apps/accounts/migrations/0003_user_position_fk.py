from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_department"),
        ("cases", "0008_reference_models"),
    ]

    operations = [
        migrations.RemoveField(model_name="user", name="position"),
        migrations.AddField(
            model_name="user",
            name="position",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users", to="cases.position",
                verbose_name="Должность",
            ),
        ),
    ]
