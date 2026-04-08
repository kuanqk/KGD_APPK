# Generated manually for TaxAuthorityDetails.region

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0016_merge_20260327_0838"),
    ]

    operations = [
        migrations.AddField(
            model_name="taxauthoritydetails",
            name="region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tax_authority_details",
                to="cases.region",
                verbose_name="Регион (если задан — дополнительный подбор реквизитов по делу)",
            ),
        ),
    ]
