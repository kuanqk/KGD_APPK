"""
Data migration: создаёт стартовые шаблоны для двух первых типов документов.
Запускается после 0001_initial (основная миграция схемы).
"""
from django.db import migrations

NOTICE_BODY = """
<p>Уведомляем Вас о необходимости явки в налоговый орган.</p>

<p><strong>Налогоплательщик:</strong> {{ taxpayer_name }}<br>
<strong>ИИН/БИН:</strong> {{ taxpayer_iin }}<br>
<strong>Номер административного дела:</strong> {{ case_number }}<br>
<strong>Основание:</strong> {{ case_basis }}</p>

<p>Просим Вас явиться в течение 5 рабочих дней с момента получения настоящего извещения
по адресу: {{ case_department }}.</p>

<p>При себе иметь документ, удостоверяющий личность, а также документы,
подтверждающие факты, изложенные в материалах дела.</p>

<p>В случае неявки без уважительной причины дело будет рассмотрено в Ваше отсутствие.</p>

<p>Дата составления: {{ date_today }}</p>
"""

PRELIMINARY_DECISION_BODY = """
<p>По результатам рассмотрения материалов административного дела
<strong>№ {{ case_number }}</strong> в отношении налогоплательщика
<strong>{{ taxpayer_name }}</strong> (ИИН/БИН: {{ taxpayer_iin }}),</p>

<p>на основании {{ case_basis }},</p>

<p>вынесено <strong>ПРЕДВАРИТЕЛЬНОЕ РЕШЕНИЕ</strong>:</p>

<p>Установлены признаки налогового нарушения. Налогоплательщику предлагается
в течение 10 рабочих дней с момента получения настоящего решения
представить письменные возражения либо явиться на заслушивание.</p>

<p>Дата составления: {{ date_today_full }}.</p>
"""


def create_initial_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    DocumentTemplate.objects.create(
        doc_type="notice",
        name="Извещение о явке (стандартное)",
        body_template=NOTICE_BODY.strip(),
        version=1,
        is_active=True,
    )

    DocumentTemplate.objects.create(
        doc_type="preliminary_decision",
        name="Предварительное решение (стандартное)",
        body_template=PRELIMINARY_DECISION_BODY.strip(),
        version=1,
        is_active=True,
    )


def remove_initial_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(
        doc_type__in=["notice", "preliminary_decision"], version=1
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_initial_templates, remove_initial_templates),
    ]
