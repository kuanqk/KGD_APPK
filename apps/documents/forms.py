from django import forms
from .models import DocumentType, DocumentTemplate


PRELIMINARY_DECISION_RISKS = [
    ("nominee",        "Номинальные директора/учредители"),
    ("fictitious",     "Фиктивные сделки (подставные компании)"),
    ("income_hidden",  "Сокрытие (занижение) доходов"),
    ("expenses",       "Завышение расходов/вычетов"),
    ("vat",            "Нарушения по НДС"),
    ("transfer",       "Трансфертное ценообразование"),
    ("offshore",       "Офшорные операции"),
    ("cash",           "Операции с наличными денежными средствами"),
    ("special_regime", "Необоснованное применение специальных налоговых режимов"),
    ("property",       "Несоответствие имущественного и финансового положения"),
    ("related",        "Операции со связанными (аффилированными) лицами"),
    ("no_activity",    "Отсутствие реальной хозяйственной деятельности"),
    ("other_tax",      "Иные нарушения налогового законодательства"),
    ("other",          "Другое"),
]


class PreliminaryDecisionForm(forms.Form):
    outgoing_number = forms.CharField(
        max_length=100,
        label="Исходящий номер",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    period_from = forms.DateField(
        label="Проверяемый период с",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    period_to = forms.DateField(
        label="по",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    criterion_1_enabled = forms.BooleanField(
        required=False,
        label="Включить критерий 1",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    criterion_1_text = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "уточните значение КНН",
        }),
    )
    criterion_2_enabled = forms.BooleanField(
        required=False,
        label="Включить критерий 2",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    criterion_2_text = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "уточните период",
        }),
    )
    criterion_3_enabled = forms.BooleanField(
        required=False,
        label="Включить критерий 3",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    criterion_3_text = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "уточните сумму убытков",
        }),
    )

    def __init__(self, *args, case=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.case = case
        for key, label in PRELIMINARY_DECISION_RISKS:
            self.fields[f"risk_{key}"] = forms.BooleanField(
                label=label,
                required=False,
                widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
            )
            self.fields[f"risk_{key}_comment"] = forms.CharField(
                label="",
                required=False,
                widget=forms.Textarea(attrs={
                    "class": "form-control form-control-sm",
                    "rows": 1,
                    "placeholder": "Комментарий (необязательно)",
                }),
            )

    def clean_period_from(self):
        return self.cleaned_data.get("period_from")

    def clean_period_to(self):
        return self.cleaned_data.get("period_to")

    def clean(self):
        cleaned = super().clean()
        period_from = cleaned.get("period_from")
        period_to = cleaned.get("period_to")
        if period_from and period_to and period_from > period_to:
            raise forms.ValidationError(
                "Дата начала периода не может быть позже даты окончания."
            )
        return cleaned


class NoticeForm(forms.Form):
    hearing_date = forms.DateField(
        label="Дата заслушивания",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    hearing_time = forms.TimeField(
        label="Время",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
    )
    hearing_address = forms.CharField(
        max_length=500,
        label="Адрес проведения",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
    inspector_phone = forms.CharField(
        max_length=50,
        required=False,
        label="Контактный телефон инспектора",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+7 (___) ___-__-__"}),
    )
    inspector_office = forms.CharField(
        max_length=50,
        required=False,
        label="Номер кабинета инспектора",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "каб. 101"}),
    )

    def __init__(self, *args, case=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.case = case
        # Prefill phone from responsible_user if available
        if case and case.responsible_user and not self.initial.get("inspector_phone"):
            self.initial["inspector_phone"] = case.responsible_user.phone or ""

    def clean_hearing_date(self):
        return self.cleaned_data.get("hearing_date")


class HearingProtocolForm(forms.Form):
    venue = forms.CharField(
        max_length=500,
        required=False,
        label="Место проведения заслушивания (адрес)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Как в протоколе; по умолчанию — адрес из реквизитов КГД",
        }),
    )
    hearing_date = forms.DateField(
        label="Дата рассмотрения",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    time_start = forms.TimeField(
        label="Время начала (ч. мин.)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
    )
    time_end = forms.TimeField(
        label="Время окончания (ч. мин.)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
    )
    official_name = forms.CharField(
        max_length=300,
        label="Ф.И.О. должностного лица",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    secretary_name = forms.CharField(
        max_length=300,
        label="Ф.И.О. секретаря",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    participant_info = forms.CharField(
        label="Сведения об участнике административной процедуры",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    participant_position = forms.CharField(
        label="Изложение позиции участника",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    dgd_position = forms.CharField(
        required=False,
        label="Позиция ДГД (выступление должностного лица)",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Изложите позицию органа государственных доходов по существу дела...",
        }),
    )
    signatory_name = forms.CharField(
        max_length=300,
        label="Ф.И.О. должностного лица (подпись)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    member_2_position = forms.CharField(
        max_length=200, required=False,
        label="Должность члена комиссии 2",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "напр. Заместитель руководителя"}),
    )
    member_2_name = forms.CharField(
        max_length=300, required=False,
        label="Ф.И.О. члена комиссии 2",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    member_3_position = forms.CharField(
        max_length=200, required=False,
        label="Должность члена комиссии 3",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "напр. Руководитель управления"}),
    )
    member_3_name = forms.CharField(
        max_length=300, required=False,
        label="Ф.И.О. члена комиссии 3",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    member_4_position = forms.CharField(
        max_length=200, required=False,
        label="Должность члена комиссии 4",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "напр. Руководитель отдела"}),
    )
    member_4_name = forms.CharField(
        max_length=300, required=False,
        label="Ф.И.О. члена комиссии 4",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    acquainted_name = forms.CharField(
        max_length=300,
        label="С протоколом ознакомлен — участник 1 (ФИО)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    acquainted_name_2 = forms.CharField(
        max_length=300, required=False,
        label="Участник 2 (ФИО)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    acquainted_name_3 = forms.CharField(
        max_length=300, required=False,
        label="Участник 3 (ФИО)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    decision_text = forms.CharField(
        required=False,
        label="Принятое решение по итогам заслушивания",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Изложите принятое решение (прекращение, назначение проверки и т.д.)",
        }),
    )

    def __init__(self, *args, case=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.case = case
        if case and not self.initial.get("venue") and not self.data:
            from apps.documents.services import _get_authority_details
            d = _get_authority_details(case)
            if d and d.address:
                self.initial["venue"] = d.address.strip()

    def clean_hearing_date(self):
        return self.cleaned_data.get("hearing_date")


class DocumentCreateForm(forms.Form):
    doc_type = forms.ChoiceField(
        choices=DocumentType.choices,
        label="Тип документа",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только типы, для которых есть активный шаблон
        available_types = (
            DocumentTemplate.objects
            .filter(is_active=True)
            .values_list("doc_type", flat=True)
            .distinct()
        )
        self.fields["doc_type"].choices = [
            (val, label)
            for val, label in DocumentType.choices
            if val in available_types
        ]
        if not self.fields["doc_type"].choices:
            self.fields["doc_type"].choices = [("", "— нет доступных шаблонов —")]
