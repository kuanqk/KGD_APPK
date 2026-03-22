"""
Data migration: обновляет шаблон «Предварительное решение» до версии 8.
Изменения:
- Убран font-size:14pt из таблицы-шапки (наследуется 12pt из base.html)
- Строка «Исполнитель» обёрнута в <p style="font-size:10pt; text-indent:0">
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

    # 1. Убрать font-size:14pt (с возможными пробелами вокруг двоеточия)
    #    Удаляем весь атрибут включая ведущую точку с запятой если есть
    body = re.sub(r';\s*font-size\s*:\s*14pt', '', body)
    body = re.sub(r'font-size\s*:\s*14pt\s*;?\s*', '', body)

    # 2. Заменить блок Исполнителя: найти <p ...> с responsible_name и добавить font-size:10pt
    #    Текущий вид: <p style="text-indent:0"><em>Исполнитель: ...
    #    Целевой вид: <p style="font-size:10pt; text-indent:0"><em>Исполнитель: ...
    body = re.sub(
        r'<p([^>]*?)>([ \t]*<em>Исполнитель:)',
        lambda m: '<p style="font-size:10pt; text-indent:0">' + m.group(2),
        body,
    )

    DocumentTemplate.objects.filter(doc_type="preliminary_decision").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="preliminary_decision",
        name="Предварительное решение (v8)",
        body_template=body.strip(),
        version=8,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=8).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="preliminary_decision"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0014_preliminary_decision_template_v7"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
