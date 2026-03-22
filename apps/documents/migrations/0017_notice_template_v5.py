"""
Data migration: обновляет шаблон «Извещение о явке» до версии 5.
Изменения:
- h3 заголовок: добавлен font-family:DejaVu,serif (кириллица не квадраты)
- Добавлен блок подписи в конец: Главный исполнитель / deputy_name /
  подпись / г. Астана, date_today
"""
from django.db import migrations

SIGNATURE_BLOCK = """\

<p style="margin-top:30px; text-indent:0">
Главный исполнитель<br>
<strong>{{ deputy_name }}</strong><br>
________________<br>
(подпись)
</p>
<p style="margin-top:10px; text-indent:0">
г. Астана, {{ date_today }}
</p>"""


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

    body = active.body_template

    # а) Добавить font-family:DejaVu,serif в h3 заголовка
    body = body.replace(
        '<h3 style="text-align:center; font-weight:bold; font-size:12pt; text-indent:0">',
        '<h3 style="text-align:center; font-weight:bold; font-size:12pt; font-family:DejaVu,serif; text-indent:0">',
    )
    # Запасной вариант — h3 без font-size
    body = body.replace(
        '<h3 style="text-align:center; font-weight:bold; text-indent:0">',
        '<h3 style="text-align:center; font-weight:bold; font-family:DejaVu,serif; text-indent:0">',
    )

    # б) Добавить блок подписи в конец
    body = body.rstrip() + SIGNATURE_BLOCK

    DocumentTemplate.objects.filter(doc_type="notice").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="notice",
        name="Извещение о явке (v5)",
        body_template=body.strip(),
        version=5,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="notice", version=5).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="notice"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0016_preliminary_decision_template_v9"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
