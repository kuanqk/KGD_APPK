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
        value = self.cleaned_data.get("period_from")
        if value and self.case and not self.case.allow_backdating:
            min_date = self.case.created_at.date()
            if value < min_date:
                raise forms.ValidationError(
                    f"Дата не может быть раньше даты создания дела ({min_date.strftime('%d.%m.%Y')})."
                )
        return value

    def clean_period_to(self):
        value = self.cleaned_data.get("period_to")
        if value and self.case and not self.case.allow_backdating:
            min_date = self.case.created_at.date()
            if value < min_date:
                raise forms.ValidationError(
                    f"Дата не может быть раньше даты создания дела ({min_date.strftime('%d.%m.%Y')})."
                )
        return value

    def clean(self):
        cleaned = super().clean()
        has_risk = any(
            cleaned.get(f"risk_{key}")
            for key, _ in PRELIMINARY_DECISION_RISKS
        )
        if not has_risk:
            raise forms.ValidationError("Необходимо отметить хотя бы один риск.")
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
        value = self.cleaned_data.get("hearing_date")
        if value and self.case and not self.case.allow_backdating:
            min_date = self.case.created_at.date()
            if value < min_date:
                raise forms.ValidationError(
                    f"Дата не может быть раньше даты создания дела ({min_date.strftime('%d.%m.%Y')})."
                )
        return value


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
