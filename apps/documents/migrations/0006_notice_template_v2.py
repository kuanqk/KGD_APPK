"""
Data migration: обновляет шаблон «Извещение о явке» до версии 2
с переменными для заслушивания (hearing_date, hearing_time, hearing_address).
"""
from django.db import migrations

NOTICE_BODY_V2 = """<p style="text-align:center"><strong>Извещение</strong></p>

<p>Департамент государственных доходов по {{ authority_name }}
в соответствии со статьей 73 Административного процедурно-процессуального
кодекса Республики Казахстан (далее – АППК РК), извещает Вас о проведении
процедуры заслушивания к административному делу об инициировании налоговой
проверки {{ case_number }} - {{ taxpayer_name }} ({{ taxpayer_iin_bin }}).</p>

<p>Процедура заслушивания может осуществляться путем приглашения участника
административной процедуры на заслушивание, в том числе посредством
видеоконференцсвязи или иных средств коммуникации, использования
информационных систем, иных способов связи, позволяющих участнику
административной процедуры изложить свою позицию.</p>

<p>Процедура заслушивания состоится: {{ hearing_date }} года
в {{ hearing_time }} часов, по адресу: {{ hearing_address }}.
Контактное лицо {{ responsible_name }}, тел. {{ responsible_phone }}.</p>

<p>Согласно пункту 3 статьи 73 АППК, вы вправе предоставить или высказать
возражение к предварительному решению по административному делу
в срок не позднее двух рабочих дней со дня его получения.</p>"""


def upgrade_notice_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    # Деактивируем старый шаблон
    DocumentTemplate.objects.filter(doc_type="notice", is_active=True).update(is_active=False)
    # Создаём новый
    DocumentTemplate.objects.create(
        doc_type="notice",
        name="Извещение о явке (v2 — с датой заслушивания)",
        body_template=NOTICE_BODY_V2.strip(),
        version=2,
        is_active=True,
    )


def downgrade_notice_template(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="notice", version=2).delete()
    DocumentTemplate.objects.filter(doc_type="notice", version=1).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_decision_templates"),
    ]

    operations = [
        migrations.RunPython(upgrade_notice_template, downgrade_notice_template),
    ]
