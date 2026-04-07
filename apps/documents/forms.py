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

    def __init__(self, *args, case=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.case = case

    def clean_hearing_date(self):
        return self.cleaned_data.get("hearing_date")


class HearingProtocolForm(forms.Form):
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
    signatory_name = forms.CharField(
        max_length=300,
        label="Ф.И.О. должностного лица (подпись)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    acquainted_name = forms.CharField(
        max_length=300,
        label="С протоколом ознакомлен (ФИО участника)",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, case=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.case = case

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
