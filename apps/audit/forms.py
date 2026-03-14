from django import forms


class AuditLogFilterForm(forms.Form):
    user_search = forms.CharField(
        label="Пользователь",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "username / ФИО"}),
    )
    action = forms.CharField(
        label="Действие",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "напр. case_created"}),
    )
    entity_type = forms.CharField(
        label="Тип объекта",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "case / decision…"}),
    )
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
