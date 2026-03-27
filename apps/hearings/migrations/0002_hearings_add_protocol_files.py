from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hearings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="hearingprotocol",
            name="signed_protocol_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="hearings/protocols/%Y/%m/",
                verbose_name="Подписанный протокол",
            ),
        ),
        migrations.AddField(
            model_name="hearingprotocol",
            name="identity_doc_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="hearings/protocols/%Y/%m/",
                verbose_name="Удостоверение личности",
            ),
        ),
        migrations.AddField(
            model_name="hearingprotocol",
            name="power_of_attorney_file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="hearings/protocols/%Y/%m/",
                verbose_name="Доверенность",
            ),
        ),
    ]
