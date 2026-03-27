from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0013_cases_basis_category_m2m"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="administrativecase",
            name="case_observers",
            field=models.ManyToManyField(
                blank=True,
                help_text="Могут просматривать дело и документы, но не создавать новые",
                related_name="observed_cases",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Наблюдатели",
            ),
        ),
    ]
