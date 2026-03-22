"""
Data migration: обновляет шаблон «Предварительное решение» до версии 7.
Причина: в БД могла остаться версия с font-family:Arial, который не
поддерживает кириллицу в xhtml2pdf. Заменяем все вхождения Arial
на DejaVu,serif и пересохраняем как v7.
"""
import re
from django.db import migrations


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    active = DocumentTemplate.objects.filter(
        doc_type="preliminary_decision", is_active=True
    ).first()
    if active is None:
        # Ищем последнюю по версии
        active = DocumentTemplate.objects.filter(
            doc_type="preliminary_decision"
        ).order_by("-version").first()
    if active is None:
        raise RuntimeError("Шаблон preliminary_decision не найден.")

    # Заменяем все font-family:Arial* (с пробелами и запасными шрифтами)
    new_body = re.sub(
        r'font-family\s*:\s*Arial[^;"\']*',
        'font-family:DejaVu,serif',
        active.body_template,
    )

    DocumentTemplate.objects.filter(doc_type="preliminary_decision").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="preliminary_decision",
        name="Предварительное решение (v7)",
        body_template=new_body.strip(),
        version=7,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=7).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="preliminary_decision"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0013_notice_template_v4"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
