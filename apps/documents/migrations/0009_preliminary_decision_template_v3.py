"""
Data migration: обновляет шаблон «Предварительное решение» до версии 3.
Полный текст из Word-документа.
Изменения:
- Добавлены реквизиты получателя (taxpayer_address) в шапке
- Три критерия (criterion_1_text / _2_text / _3_text)
- Риски через {% for item in risk_items %} + отдельная строка {{ risk_other_comment }}
- Подпись с deputy_position и deputy_name
- Исполнитель: responsible_name / responsible_phone
"""
from django.db import migrations

PRELIMINARY_DECISION_BODY_V3 = """\
<div style="text-align:right; margin-bottom:20px">
  <strong>{{ outgoing_number }}</strong>
</div>
<div style="text-align:right; margin-bottom:20px">
  <strong>{{ taxpayer_name }}</strong><br>
  <strong>{{ taxpayer_iin_bin }}</strong><br>
  <strong>{{ taxpayer_address }}</strong>
</div>

<h3 style="text-align:center">Предварительное решение<br>
по назначению комплексной/тематической налоговой проверки</h3>

<p>{{ authority_name }} (далее &#8211; Департамент) в соответствии со статьей 42
и пунктом 3 статьи 151 Налогового кодекса Республики Казахстан на основе
анализа налоговой отчетности, данных из информационных систем органов
государственных доходов, сведений, полученных от уполномоченных
государственных органов и иных источников, выявлены признаки искажения
объектов налогообложения и (или) объектов, связанных с налогообложением
за период с {{ period_from }} года по {{ period_to }} года
по основным критериям:</p>

<p>1. несоответствие коэффициента налоговой нагрузки к среднеотраслевому
значению {{ criterion_1_text }};</p>

<p>2. минимизация налоговых обязательств путем представления дополнительных
форм налоговой отчетности с уменьшением сумм исчисленных налогов, в том
числе за ранее проверенный период {{ criterion_2_text }};</p>

<p>3. несоответствие сумм убытков, переносимых на последующие периоды
{{ criterion_3_text }}.</p>

<p>Вместе с тем, установлены риски нарушений несоблюдения налогового
законодательства, связанные с определением налогооблагаемого дохода,
вычетов и возникновением убытка, в том числе:</p>

{% for item in risk_items %}
<p>- {{ item.label }}{% if item.comment %}, {{ item.comment }}{% endif %};</p>
{% endfor %}
<p>- {{ risk_other_comment }}.</p>

<p>Указанные признаки выражаются в совокупности взаимосвязанных
хозяйственных операций и могут оказывать влияние на налоговые обязательства
налогоплательщика в течение всего проверяемого периода и требуют оценки
полноты, достоверности и корректности формирования налоговой базы в целом.</p>

<p>Пунктом 3 статьи 190 Налогового кодекса определено, что налоговый учет
основывается на данных бухгалтерского учета. Согласно Закону Республики
Казахстан от 28 февраля 2007 года &#8470; 234 &#171;О бухгалтерском учете и финансовой
отчетности&#187; бухгалтерская документация включает в себя первичные документы,
регистры бухгалтерского учета, финансовую отчетность и учетную политику,
бухгалтерские записи производятся на основании первичных документов.</p>

<p>В случае проведения налоговой проверки органы государственных доходов
вправе истребовать у налогоплательщика учетную документацию, письменные
пояснения, запрашивать у государственных органов, банков и иных организаций
необходимые документы и сведения, проводить встречные проверки и
осуществлять иные действия, предусмотренные налоговым законодательством
Республики Казахстан.</p>

<p>Обращаем Ваше внимание, что в ходе проведения налоговой проверки
корректируются объекты налогообложения и (или) объекты, связанные с
налогообложением путем дачи оценки проверяемым документам
налогоплательщиков исключительно в налоговых целях, при этом допускается
выявление дополнительных нарушений, непосредственно связанных с предметом
проверки и обнаруженных в пределах проверяемого периода.</p>

<p>Руководствуясь статьей 73 Административного процедурно-процессуального
Кодекса Республики Казахстан (далее &#8211; АППК) Департамент просит выразить
свою позицию к предварительному решению по административному делу не
позднее чем пяти рабочих дней до принятия административного акта.</p>

<p style="margin-top:30px">
<strong>{{ deputy_position }}</strong> &nbsp;&nbsp;&nbsp; подпись
&nbsp;&nbsp;&nbsp; <strong>{{ deputy_name }}</strong>
</p>

<p style="margin-top:20px">С предварительным решением ознакомлен:
(ФИО, должность, либо по доверенности, дата, подпись, печать при ее наличии)</p>

<p style="margin-top:20px"><em>Исполнитель: {{ responsible_name }},
тел. {{ responsible_phone }}</em></p>"""


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="preliminary_decision",
        name="Предварительное решение (v3)",
        body_template=PRELIMINARY_DECISION_BODY_V3.strip(),
        version=3,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=3).delete()
    restored = DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=2).first()
    if not restored:
        restored = DocumentTemplate.objects.filter(doc_type="preliminary_decision", version=1).first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0008_preliminary_decision_template_v2"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
