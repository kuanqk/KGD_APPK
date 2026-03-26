from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliveryrecord",
            name="proof_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="delivery/proofs/%Y/%m/",
                verbose_name="Файл подтверждения",
            ),
        ),
    ]
