"""
Data migration: обновляет шаблон «Извещение о явке» до версии 4.
Изменения: добавлен заголовок h3 в начало тела шаблона,
так как base.html больше не рендерит название типа документа.
"""
from django.db import migrations

NOTICE_HEADING = (
    '<h3 style="text-align:center; font-weight:bold; font-family:Arial; '
    'font-size:14pt; text-indent:0; margin-bottom:20px">ИЗВЕЩЕНИЕ О ЯВКЕ</h3>\n\n'
)


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    v3 = DocumentTemplate.objects.filter(doc_type="notice", version=3).first()
    if v3 is None:
        raise RuntimeError("Шаблон notice v3 не найден — убедитесь, что миграция 0007 применена.")

    DocumentTemplate.objects.filter(doc_type="notice").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="notice",
        name="Извещение о явке (v4)",
        body_template=(NOTICE_HEADING + v3.body_template).strip(),
        version=4,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="notice", version=4).delete()
    restored = DocumentTemplate.objects.filter(doc_type="notice", version=3).first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_preliminary_decision_template_v6"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
