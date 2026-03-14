from django import forms
from apps.cases.models import CaseStatus


class ReportFilterForm(forms.Form):
    date_from = forms.DateField(
        label="Дата с",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    date_to = forms.DateField(
        label="Дата по",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    region = forms.CharField(
        label="Регион",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Все регионы"}),
    )
    department = forms.CharField(
        label="Подразделение",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Все"}),
    )
    status = forms.ChoiceField(
        label="Статус дела",
        required=False,
        choices=[("", "Все статусы")] + list(CaseStatus.choices),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    responsible_user = forms.IntegerField(
        label="Ответственный (ID)",
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": "ID"}),
    )

    def get_filters(self) -> dict:
        """Возвращает очищенный dict фильтров для передачи в services."""
        if not self.is_valid():
            return {}
        cd = self.cleaned_data
        filters = {}
        if cd.get("date_from"):
            filters["date_from"] = cd["date_from"]
        if cd.get("date_to"):
            filters["date_to"] = cd["date_to"]
        if cd.get("region"):
            filters["region"] = cd["region"]
        if cd.get("department"):
            filters["department"] = cd["department"]
        if cd.get("status"):
            filters["status"] = cd["status"]
        if cd.get("responsible_user"):
            from apps.accounts.models import User
            try:
                filters["responsible_user"] = User.objects.get(pk=cd["responsible_user"])
            except User.DoesNotExist:
                pass
        return filters
