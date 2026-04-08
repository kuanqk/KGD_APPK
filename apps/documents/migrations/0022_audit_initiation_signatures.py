"""
Дополняет шаблон «Инициирование внеплановой проверки» блоком подписи/даты (обращение 71).
"""

from django.db import migrations


SIGNATURE_BLOCK = """

<p style="margin-top:24px; text-indent:0"><strong>Подпись должностного лица:</strong></p>
<table width="100%" style="margin-top:8px">
<tr>
  <td style="width:55%">{{ deputy_name|default:"________________" }}<br>
  <em>{{ deputy_position|default:"должность" }}</em></td>
  <td style="width:45%; text-align:right">«____» ________________ {{ date_today_full }} г.<br>
  <em>(подпись, дата)</em></td>
</tr>
</table>
"""


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    active = DocumentTemplate.objects.filter(
        doc_type="audit_initiation", is_active=True
    ).first()
    if active is None:
        active = DocumentTemplate.objects.filter(
            doc_type="audit_initiation"
        ).order_by("-version").first()
    if active is None:
        return

    body = (active.body_template or "").rstrip()
    if "Подпись должностного лица" in body:
        return

    DocumentTemplate.objects.filter(doc_type="audit_initiation").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="audit_initiation",
        name=f"{active.name} (подписи)",
        body_template=(body + SIGNATURE_BLOCK).strip(),
        version=(active.version or 0) + 1,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    latest = DocumentTemplate.objects.filter(
        doc_type="audit_initiation"
    ).order_by("-version").first()
    if latest and "Подпись должностного лица" in (latest.body_template or ""):
        latest.delete()
        prev = DocumentTemplate.objects.filter(
            doc_type="audit_initiation"
        ).order_by("-version").first()
        if prev:
            prev.is_active = True
            prev.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0021_hearing_protocol_v4"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
