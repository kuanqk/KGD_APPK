from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="administrativecase",
            name="allow_backdating",
            field=models.BooleanField(default=False, verbose_name="Разрешён ввод задним числом"),
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="backdating_allowed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="backdating_approvals",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Разрешил задним числом",
            ),
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="backdating_allowed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Дата разрешения задним числом"),
        ),
        migrations.AddField(
            model_name="administrativecase",
            name="backdating_comment",
            field=models.TextField(blank=True, verbose_name="Комментарий к вводу задним числом"),
        ),
    ]
