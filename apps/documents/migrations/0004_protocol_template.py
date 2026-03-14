"""
Data migration: шаблон Протокола заслушивания (Sprint 5).
"""
from django.db import migrations

PROTOCOL_BODY = """
<p>Протокол заслушивания составлен в рамках административного дела
<strong>№ {{ case_number }}</strong>.</p>

<p><strong>Налогоплательщик:</strong> {{ taxpayer_name }}<br>
<strong>ИИН/БИН:</strong> {{ taxpayer_iin }}<br>
<strong>Основание дела:</strong> {{ case_basis }}<br>
<strong>Регион:</strong> {{ case_region }}</p>

<p>Заслушивание проведено {{ date_today_full }}.</p>

<p><strong>Краткое содержание:</strong></p>
<p>{{ result_summary|default:"" }}</p>

<p>В ходе заслушивания налогоплательщику предоставлена возможность изложить
свою позицию и представить дополнительные документы.</p>

<p>По итогам заслушивания будет вынесено итоговое решение в течение
2 (двух) рабочих дней с момента подписания настоящего протокола.</p>

<p>Ответственный: {{ responsible_name }}<br>
{{ responsible_position }}</p>

<p>Дата: {{ date_today_full }}.</p>
"""


def create_protocol_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.create(
        doc_type="hearing_protocol",
        name="Протокол заслушивания (стандартный)",
        body_template=PROTOCOL_BODY.strip(),
        version=1,
        is_active=True,
    )


def remove_protocol_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="hearing_protocol", version=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_return_templates"),
    ]

    operations = [
        migrations.RunPython(create_protocol_template, remove_protocol_template),
    ]
