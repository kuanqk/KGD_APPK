from django import forms


class HearingScheduleForm(forms.Form):
    hearing_date = forms.DateField(
        label="Дата заслушивания",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    hearing_time = forms.TimeField(
        label="Время",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    location = forms.CharField(
        max_length=300,
        label="Место проведения",
        widget=forms.TextInput(attrs={"placeholder": "Адрес или ссылка на конференцию"}),
    )
    format = forms.ChoiceField(
        label="Формат",
        choices=[
            ("in_person", "Очно"),
            ("remote", "Дистанционно"),
            ("mixed", "Смешанный формат"),
        ],
        widget=forms.RadioSelect,
    )
    participants = forms.CharField(
        label="Участники",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "По одному участнику на строку:\nИванов И.И., начальник отдела\nПетров П.П., инспектор",
        }),
        help_text="Каждый участник — с новой строки",
    )
    notes = forms.CharField(
        label="Примечания",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean_hearing_date(self):
        from datetime import date
        value = self.cleaned_data["hearing_date"]
        if value < date.today():
            raise forms.ValidationError("Дата заслушивания не может быть в прошлом.")
        return value

    def clean_participants(self):
        raw = self.cleaned_data.get("participants", "")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return lines


class ProtocolCreateForm(forms.Form):
    result_summary = forms.CharField(
        label="Краткое содержание / итог заслушивания",
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "Опишите ход заседания и принятые решения...",
        }),
    )
