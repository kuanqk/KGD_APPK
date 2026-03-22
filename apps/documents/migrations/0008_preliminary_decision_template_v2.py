"""
Data migration: обновляет шаблон «Предварительное решение» до версии 2.
Изменения:
- Добавлены переменные: outgoing_number, period_from, period_to
- Добавлен цикл по risk_items (список рисков с метками и комментариями)
- authority_name берётся из справочника реквизитов
"""
from django.db import migrations

PRELIMINARY_DECISION_BODY_V2 = """\
<p><strong>Исходящий №:</strong> {{ outgoing_number }} от {{ date_today }} г.</p>

<p>{{ authority_name }} в рамках административного производства по делу \
<strong>№ {{ case_number }}</strong> в отношении налогоплательщика \
<strong>{{ taxpayer_name }}</strong> (ИИН/БИН: {{ taxpayer_iin_bin }}), \
по результатам анализа финансово-хозяйственной деятельности \
за период с <strong>{{ period_from }}</strong> по <strong>{{ period_to }}</strong>, \
в соответствии со статьями 70–73 Административного процедурно-процессуального \
кодекса Республики Казахстан выносит:</p>

<p style="text-align:center"><strong>ПРЕДВАРИТЕЛЬНОЕ РЕШЕНИЕ</strong></p>

<p>По результатам предварительного изучения деятельности налогоплательщика \
установлены следующие риски, являющиеся основаниями для инициирования \
внеплановой тематической налоговой проверки:</p>

{% for item in risk_items %}<p>{{ forloop.counter }}. {{ item.label }}{% if item.comment %}: <em>{{ item.comment }}</em>{% endif %}.</p>
{% endfor %}

<p>На основании выявленных рисков предварительно принимается решение об \
инициировании внеплановой тематической налоговой проверки.</p>

<p>Согласно пункту 3 статьи 73 АППК РК, Вы вправе предоставить возражение к \
предварительному решению в срок не позднее двух рабочих дней со дня его получения.</p>"""


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="preliminary_decision",
        name="Предварительное решение (v2)",
        body_template=PRELIMINARY_DECISION_BODY_V2.strip(),
        version=2,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=2).delete()
    restored = DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=1).first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0007_notice_template_v3"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
