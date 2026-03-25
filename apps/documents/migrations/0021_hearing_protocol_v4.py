"""
Data migration: обновляет шаблон «Протокол заслушивания» до версии 4.
Изменение: убирает лишний символ «>» перед текстом заголовка,
оставшийся после regex-замены в v3.
"""
import re
from django.db import migrations


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    active = DocumentTemplate.objects.filter(
        doc_type="hearing_protocol", is_active=True
    ).first()
    if active is None:
        active = DocumentTemplate.objects.filter(
            doc_type="hearing_protocol"
        ).order_by("-version").first()
    if active is None:
        raise RuntimeError("Шаблон hearing_protocol не найден.")

    body = active.body_template

    # Убираем лишний «>» в начале содержимого заголовочного <p>:
    # Варианты: ">><strong>...", ">\n>...", "> Протокол..." и т.п.
    body = re.sub(
        r'(<p[^>]*>)\s*>\s*((?:<strong>)?\s*Протокол заслушивания)',
        r'\1\2',
        body,
    )

    DocumentTemplate.objects.filter(doc_type="hearing_protocol").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="hearing_protocol",
        name="Протокол заслушивания (v4)",
        body_template=body.strip(),
        version=4,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="hearing_protocol", version=4).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="hearing_protocol"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0020_hearing_protocol_template_v3"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
