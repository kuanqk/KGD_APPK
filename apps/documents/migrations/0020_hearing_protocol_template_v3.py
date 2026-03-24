"""
Data migration: обновляет шаблон «Протокол заслушивания» до версии 3.
Изменения:
- Заголовок <p style="...font-weight:bold..."> → font-weight убран из style,
  текст обёрнут в <strong> (xhtml2pdf каскадировал bold на весь документ)
- Убраны <hr> теги
- Убраны text-decoration:underline из style
- Убраны все оставшиеся font-weight:bold из inline style
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

    # 1. Убрать <hr> теги
    body = re.sub(r'<hr\b[^>]*/?>|<hr>', '', body)

    # 2. Убрать text-decoration:underline из style (с ведущей ; или без)
    body = re.sub(r';\s*text-decoration\s*:\s*underline\b', '', body)
    body = re.sub(r'text-decoration\s*:\s*underline\b\s*;?\s*', '', body)

    # 3. Заменить заголовочный <p> с font-weight:bold:
    #    убрать bold из style, обернуть текст в <strong>
    body = re.sub(
        r'<p(\s+style="[^"]*?);\s*font-weight\s*:\s*bold([^"]*")(.*?)</p>',
        lambda m: f'<p{m.group(1)}{m.group(2)}><strong>{m.group(3).strip()}</strong></p>',
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r'<p(\s+style=")\s*font-weight\s*:\s*bold\s*;?\s*([^"]*")(.*?)</p>',
        lambda m: f'<p{m.group(1)}{m.group(2)}><strong>{m.group(3).strip()}</strong></p>',
        body,
        flags=re.DOTALL,
    )

    # 4. Убрать любые оставшиеся font-weight:bold из inline style (catch-all)
    body = re.sub(r';\s*font-weight\s*:\s*bold\b', '', body)
    body = re.sub(r'font-weight\s*:\s*bold\b\s*;?\s*', '', body)

    DocumentTemplate.objects.filter(doc_type="hearing_protocol").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="hearing_protocol",
        name="Протокол заслушивания (v3)",
        body_template=body.strip(),
        version=3,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="hearing_protocol", version=3).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="hearing_protocol"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0019_hearing_protocol_template_v2"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
