"""
Data migration: обновляет шаблон «Извещение о явке» до версии 6.
Изменения: h3 заголовок заменён на <p> — xhtml2pdf теряет шрифт в h3,
что приводит к отображению кириллицы квадратами.
"""
import re
from django.db import migrations

HEADING_P = (
    '<p style="text-align:center; font-weight:bold; '
    'font-family:DejaVu,serif; text-indent:0; margin:20px 0">\n'
    'ИЗВЕЩЕНИЕ О ЯВКЕ\n'
    '</p>'
)


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    active = DocumentTemplate.objects.filter(
        doc_type="notice", is_active=True
    ).first()
    if active is None:
        active = DocumentTemplate.objects.filter(
            doc_type="notice"
        ).order_by("-version").first()
    if active is None:
        raise RuntimeError("Шаблон notice не найден.")

    # Заменяем любой <h3 ...>ИЗВЕЩЕНИЕ О ЯВКЕ</h3> на <p>
    body = re.sub(
        r'<h3[^>]*>\s*ИЗВЕЩЕНИЕ О ЯВКЕ\s*</h3>',
        HEADING_P,
        active.body_template,
    )

    DocumentTemplate.objects.filter(doc_type="notice").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="notice",
        name="Извещение о явке (v6)",
        body_template=body.strip(),
        version=6,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="notice", version=6).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="notice"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0017_notice_template_v5"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
