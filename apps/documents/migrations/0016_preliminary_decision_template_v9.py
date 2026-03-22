"""
Data migration: обновляет шаблон «Предварительное решение» до версии 9.
Изменения:
- h3 заголовок: упрощён стиль до text-align:center; font-weight:bold; text-indent:0
- risk_other_comment: строка "−." не выводится если поле пустое
- «С предварительным решением ознакомлен» — жирный текст
"""
import re
from django.db import migrations


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    active = DocumentTemplate.objects.filter(
        doc_type="preliminary_decision", is_active=True
    ).first()
    if active is None:
        active = DocumentTemplate.objects.filter(
            doc_type="preliminary_decision"
        ).order_by("-version").first()
    if active is None:
        raise RuntimeError("Шаблон preliminary_decision не найден.")

    body = active.body_template

    # а) Упростить стиль h3 (убрать font-size и margin, оставить bold + center)
    body = re.sub(
        r'<h3\s+style="[^"]*">',
        '<h3 style="text-align:center; font-weight:bold; text-indent:0">',
        body,
    )

    # б) Условный вывод risk_other_comment
    body = body.replace(
        '<p style="text-indent:0">&#8722; {{ risk_other_comment }}.</p>',
        '{% if risk_other_comment %}<p style="text-indent:0">&#8722; {{ risk_other_comment }}.</p>{% endif %}',
    )

    # в) «С предварительным решением ознакомлен» — жирный
    body = re.sub(
        r'<p([^>]*)>С предварительным решением ознакомлен:\n'
        r'(\(ФИО, должность, либо по доверенности, дата, подпись, печать при ее наличии\))</p>',
        r'<p\1><strong>С предварительным решением ознакомлен:</strong>\n\2</p>',
        body,
    )

    DocumentTemplate.objects.filter(doc_type="preliminary_decision").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="preliminary_decision",
        name="Предварительное решение (v9)",
        body_template=body.strip(),
        version=9,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=9).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="preliminary_decision"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0015_preliminary_decision_template_v8"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
