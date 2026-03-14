"""
Data migration: шаблоны итоговых решений (Sprint 6).
- Решение о прекращении административного дела
- Инициирование внеплановой тематической проверки
- Приказ о назначении внеплановой налоговой проверки
"""
from django.db import migrations

TERMINATION_BODY = """
<p>По результатам рассмотрения материалов административного дела
<strong>№ {{ case_number }}</strong> в отношении налогоплательщика
<strong>{{ taxpayer_name }}</strong> (ИИН/БИН: {{ taxpayer_iin }}),</p>

<p>принимая во внимание протокол заслушивания и представленные материалы,
руководствуясь Кодексом Республики Казахстан об административных правонарушениях,</p>

<p><strong>РЕШЕНО:</strong></p>

<p>Административное дело № {{ case_number }} в отношении {{ taxpayer_name }}
<strong>ПРЕКРАТИТЬ</strong>.</p>

<p>Основание: {{ case_basis }}.</p>

<p>Дата вынесения решения: {{ date_today_full }}.</p>

<p>Ответственный: {{ responsible_name }}<br>
{{ responsible_position }}</p>
"""

AUDIT_INITIATION_BODY = """
<p>На основании результатов рассмотрения административного дела
<strong>№ {{ case_number }}</strong> в отношении налогоплательщика
<strong>{{ taxpayer_name }}</strong> (ИИН/БИН: {{ taxpayer_iin }}),</p>

<p>в связи с выявленными признаками налоговых нарушений,</p>

<p><strong>ИНИЦИИРУЕТСЯ</strong> проведение внеплановой тематической налоговой проверки.</p>

<p>Предмет проверки: проверка правильности исчисления и своевременности
уплаты налогов и других обязательных платежей в бюджет за проверяемый период.</p>

<p>Основание: {{ case_basis }}.<br>
Регион: {{ case_region }}.<br>
Дата инициирования: {{ date_today_full }}.</p>

<p>Ответственный: {{ responsible_name }}<br>
{{ responsible_position }}</p>
"""

AUDIT_ORDER_BODY = """
<p><strong>ПРИКАЗ № </strong> о назначении внеплановой налоговой проверки</p>

<p>В соответствии с Кодексом Республики Казахстан «О налогах и других
обязательных платежах в бюджет» (Налоговый кодекс),</p>

<p><strong>НАЗНАЧИТЬ</strong> внеплановую тематическую налоговую проверку в отношении:</p>

<p><strong>Налогоплательщик:</strong> {{ taxpayer_name }}<br>
<strong>ИИН/БИН:</strong> {{ taxpayer_iin }}<br>
<strong>Адрес:</strong> {{ taxpayer_address|default:"не указан" }}<br>
<strong>Основание дела № {{ case_number }}:</strong> {{ case_basis }}</p>

<p>Проверяемый период: определяется отдельным решением.<br>
Вопросы, подлежащие проверке: правильность исчисления и своевременность
уплаты налогов и других обязательных платежей в бюджет.</p>

<p>Дата приказа: {{ date_today_full }}.</p>

<p>Ответственный: {{ responsible_name }}<br>
{{ responsible_position }}</p>
"""


def create_decision_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    DocumentTemplate.objects.create(
        doc_type="termination_decision",
        name="Решение о прекращении административного дела",
        body_template=TERMINATION_BODY.strip(),
        version=1,
        is_active=True,
    )

    DocumentTemplate.objects.create(
        doc_type="audit_initiation",
        name="Инициирование внеплановой тематической проверки",
        body_template=AUDIT_INITIATION_BODY.strip(),
        version=1,
        is_active=True,
    )

    DocumentTemplate.objects.create(
        doc_type="audit_order",
        name="Приказ о назначении внеплановой налоговой проверки",
        body_template=AUDIT_ORDER_BODY.strip(),
        version=1,
        is_active=True,
    )


def remove_decision_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(
        doc_type__in=["termination_decision", "audit_initiation", "audit_order"],
        version=1,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_protocol_template"),
    ]

    operations = [
        migrations.RunPython(create_decision_templates, remove_decision_templates),
    ]
