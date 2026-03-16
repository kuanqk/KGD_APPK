from django.db import migrations

REGIONS = [
    ("01", "Акмолинская область"),
    ("02", "Актюбинская область"),
    ("03", "Алматинская область"),
    ("04", "Атырауская область"),
    ("05", "Восточно-Казахстанская область"),
    ("06", "Жамбылская область"),
    ("07", "Западно-Казахстанская область"),
    ("08", "Карагандинская область"),
    ("09", "Костанайская область"),
    ("10", "Кызылординская область"),
    ("11", "Мангистауская область"),
    ("12", "Павлодарская область"),
    ("13", "Северо-Казахстанская область"),
    ("14", "Туркестанская область"),
    ("15", "Абайская область"),
    ("16", "Жетысуская область"),
    ("17", "Улытауская область"),
    ("ААА", "г. Алматы"),
    ("АСТ", "г. Астана"),
    ("ШМК", "г. Шымкент"),
]

BASES = [
    ("kameral", "Камеральный контроль", ""),
    ("complaint", "Жалоба налогоплательщика", ""),
    ("audit_result", "Результаты проверки", ""),
    ("other", "Иное", ""),
]

CATEGORIES = [
    ("nds", "НДС"),
    ("kpn", "КПН"),
    ("ipn", "ИПН"),
    ("akciz", "Акциз"),
    ("other", "Иное"),
]


def load_initial_data(apps, schema_editor):
    Region = apps.get_model("cases", "Region")
    CaseBasis = apps.get_model("cases", "CaseBasis")
    CaseCategory = apps.get_model("cases", "CaseCategory")

    for code, name in REGIONS:
        Region.objects.get_or_create(code=code, defaults={"name": name})

    for code, name, legal_ref in BASES:
        CaseBasis.objects.get_or_create(code=code, defaults={"name": name, "legal_ref": legal_ref})

    for code, name in CATEGORIES:
        CaseCategory.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0008_reference_models"),
    ]

    operations = [
        migrations.RunPython(load_initial_data, migrations.RunPython.noop),
    ]
