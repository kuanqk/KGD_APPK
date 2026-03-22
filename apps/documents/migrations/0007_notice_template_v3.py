"""
Data migration: обновляет шаблон «Извещение о явке» до версии 3.
Изменения:
- Убрана строка «Извещение» в начале тела (дублирует заголовок base.html)
- Убран «Департамент государственных доходов по» перед authority_name
  (теперь authority_name должен содержать полное название органа)
- Тело обновляется через update() — работает даже если v2 уже в БД
"""
from django.db import migrations

NOTICE_BODY_V3 = """<p>{{ authority_name }}
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


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    # Деактивируем все существующие шаблоны NOTICE
    DocumentTemplate.objects.filter(doc_type="notice").update(is_active=False)
    # Создаём v3 как единственный активный
    DocumentTemplate.objects.create(
        doc_type="notice",
        name="Извещение о явке (v3)",
        body_template=NOTICE_BODY_V3.strip(),
        version=3,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="notice", version=3).delete()
    # Восстанавливаем v2 если есть, иначе v1
    restored = DocumentTemplate.objects.filter(doc_type="notice", version=2).first()
    if not restored:
        restored = DocumentTemplate.objects.filter(doc_type="notice", version=1).first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0006_notice_template_v2"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
