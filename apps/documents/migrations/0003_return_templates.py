"""
Data migration: шаблоны для ветки возврата почтового отправления.
Sprint 4 — Акт налогового обследования + Запрос в ДЭР.
"""
from django.db import migrations

INSPECTION_ACT_BODY = """
<p>Настоящий акт составлен по результатам налогового обследования в рамках
административного дела <strong>№ {{ case_number }}</strong>.</p>

<p><strong>Налогоплательщик:</strong> {{ taxpayer_name }}<br>
<strong>ИИН/БИН:</strong> {{ taxpayer_iin }}<br>
<strong>Тип:</strong> {{ taxpayer_type }}<br>
<strong>Адрес:</strong> {{ taxpayer_address|default:"не указан" }}<br>
<strong>Регион:</strong> {{ case_region }}<br>
<strong>Основание:</strong> {{ case_basis }}</p>

<p>В ходе обследования установлено, что почтовое отправление с извещением о явке
возвращено без вручения адресату. По месту регистрации (юридическому адресу)
налогоплательщик не обнаружен / деятельность не ведётся.</p>

<p>На основании изложенного составлен настоящий акт налогового обследования.</p>

<p>Дата составления: {{ date_today_full }}.</p>
"""

DER_REQUEST_BODY = """
<p>В соответствии с требованиями налогового законодательства Республики Казахстан,
в рамках административного дела <strong>№ {{ case_number }}</strong>,</p>

<p>прошу оказать содействие в установлении местонахождения налогоплательщика:</p>

<p><strong>Наименование / ФИО:</strong> {{ taxpayer_name }}<br>
<strong>ИИН/БИН:</strong> {{ taxpayer_iin }}<br>
<strong>Последний известный адрес:</strong> {{ taxpayer_address|default:"не указан" }}<br>
<strong>Основание дела:</strong> {{ case_basis }}</p>

<p>Извещение о явке, направленное по адресу регистрации, возвращено без вручения.
Акт налогового обследования составлен {{ date_today }}.</p>

<p>Прошу сообщить актуальные сведения о местонахождении налогоплательщика
в срок до 5 рабочих дней с момента получения настоящего запроса.</p>

<p>Ответственный: {{ responsible_name }}<br>
{{ responsible_position }}</p>

<p>Дата: {{ date_today_full }}.</p>
"""


def create_return_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    DocumentTemplate.objects.create(
        doc_type="inspection_act",
        name="Акт налогового обследования (стандартный)",
        body_template=INSPECTION_ACT_BODY.strip(),
        version=1,
        is_active=True,
    )

    DocumentTemplate.objects.create(
        doc_type="der_request",
        name="Запрос в ДЭР об оказании содействия (стандартный)",
        body_template=DER_REQUEST_BODY.strip(),
        version=1,
        is_active=True,
    )


def remove_return_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(
        doc_type__in=["inspection_act", "der_request"], version=1
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_initial_templates"),
    ]

    operations = [
        migrations.RunPython(create_return_templates, remove_return_templates),
    ]
