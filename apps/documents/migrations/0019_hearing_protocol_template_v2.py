"""
Data migration: создаёт шаблон «Протокол заслушивания» версии 2.
"""
from django.db import migrations

BODY = """\
<p style="text-align:center; font-weight:bold; text-indent:0">
Протокол заслушивания</p>

<table width="100%" style="margin-bottom:10px">
<tr>
  <td style="width:50%">{{ authority_address }}<br>
  <em>(место рассмотрения)</em></td>
  <td style="width:50%; text-align:right">
  «{{ hearing_date_day }}» {{ hearing_date_month }} {{ hearing_date_year }}г.<br>
  <em>(дата рассмотрения)</em></td>
</tr>
</table>

<p style="text-indent:0"><strong>Время начала рассмотрения:</strong>
{{ time_start }} ч. мин.</p>

<p style="text-indent:0"><strong>Время окончания рассмотрения:</strong>
{{ time_end }} ч. мин.</p>

<p style="text-indent:0"><strong>Наименование административного органа:</strong>
{{ authority_name }}</p>

<p style="text-indent:0"><strong>Ф.И.О. должностного лица:</strong>
{{ official_name }}</p>

<p style="text-indent:0"><strong>Ф.И.О. секретаря:</strong> {{ secretary_name }}</p>

<p style="text-indent:0"><strong>Сведения об участнике административной процедуры
и (или) ином лице, участвующем в административном деле:</strong>
{{ participant_info }}</p>

<p style="text-indent:0"><strong>Содержание рассматриваемого вопроса:</strong>
Проведение налоговой проверки на основании решения налогового
органа в отношении {{ taxpayer_name }} БИН/ИИН {{ taxpayer_iin_bin }}.</p>

<p style="text-indent:0"><strong>Выступление должностного лица органа государственных
доходов:</strong><br>
В соответствии с пунктом 5 статьи 144 Предпринимательского
кодекса РК внеплановой проверке подлежат факты и обстоятельства,
выявленные в отношении конкретных субъектов и объектов
предпринимательства и послужившие основанием для назначения
данной внеплановой проверки.<br>
В связи с чем, Департаментом государственных доходов проведен
детальный анализ финансово-хозяйственной деятельности на основе
представленной Вами налоговой отчетности, сведений, полученных
из информационных систем КГД МФ РК, а также других документов
и сведений, полученных из различных источников информации.<br>
Вместе с тем, в случае согласия с указанными фактами нарушений
Вы имеете право для самостоятельного устранения нарушений путем
представления налоговой отчетности и (или) уплаты налогов и
платежей в бюджет.<br>
В случае несогласия будет назначена налоговая проверка в
соответствии с подпунктом 3) пункта 3 статьи 153 Налогового
кодекса РК.</p>

<p style="text-indent:0"><strong>Изложение позиции участника:</strong>
{{ participant_position }}</p>

<br><br><br><br><br>

<p style="text-indent:0">согласие по устранению нарушений путем предоставления ДФНО
и уплаты налогов либо несогласие путем представления пояснения
и назначения налоговой проверки.</p>

<table width="100%" style="margin-top:30px">
<tr>
  <td style="width:60%">{{ signatory_name }}<br>
  <em>(Ф.И.О. должностного лица)</em></td>
  <td style="width:40%; text-align:right">________________<br>
  <em>(подпись)</em></td>
</tr>
<tr>
  <td style="padding-top:20px">{{ secretary_name }}<br>
  <em>(Ф.И.О. секретаря)</em></td>
  <td style="padding-top:20px; text-align:right">________________<br>
  <em>(подпись)</em></td>
</tr>
</table>

<p style="margin-top:30px; text-indent:0">
<strong>С протоколом заслушивания ознакомлен:</strong><br>
{{ acquainted_name }}<br>
<em>(Ф.И.О. участника, подпись)</em></p>"""


def upgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="hearing_protocol").update(is_active=False)
    DocumentTemplate.objects.create(
        doc_type="hearing_protocol",
        name="Протокол заслушивания (v2)",
        body_template=BODY.strip(),
        version=2,
        is_active=True,
    )


def downgrade(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    DocumentTemplate.objects.filter(doc_type="hearing_protocol", version=2).delete()
    restored = DocumentTemplate.objects.filter(
        doc_type="hearing_protocol"
    ).order_by("-version").first()
    if restored:
        restored.is_active = True
        restored.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0018_notice_template_v6"),
    ]

    operations = [
        migrations.RunPython(upgrade, downgrade),
    ]
