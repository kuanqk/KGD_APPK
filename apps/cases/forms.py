from django import forms
from apps.accounts.models import User
from .models import AdministrativeCase, Department, Taxpayer, CaseBasis, TaxpayerType


class TaxpayerForm(forms.ModelForm):
    class Meta:
        model = Taxpayer
        fields = ["iin_bin", "name", "taxpayer_type", "address", "phone", "email"]
        widgets = {
            "iin_bin": forms.TextInput(attrs={"placeholder": "12 цифр", "maxlength": 12}),
            "address": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "iin_bin": "ИИН/БИН",
            "name": "Наименование / ФИО",
            "taxpayer_type": "Тип",
        }


class CaseCreateForm(forms.Form):
    # Данные НП
    iin_bin = forms.CharField(
        max_length=12,
        label="ИИН/БИН",
        widget=forms.TextInput(attrs={"placeholder": "12 цифр"}),
    )
    taxpayer_name = forms.CharField(max_length=500, label="Наименование / ФИО")
    taxpayer_type = forms.ChoiceField(choices=TaxpayerType.choices, label="Тип НП")
    taxpayer_address = forms.CharField(
        required=False,
        label="Адрес НП",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    taxpayer_phone = forms.CharField(max_length=30, required=False, label="Телефон НП")
    taxpayer_email = forms.EmailField(required=False, label="Email НП")

    # Данные дела
    region = forms.CharField(max_length=100, label="Регион")
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Подразделение",
        empty_label="— выберите подразделение —",
    )
    basis = forms.ChoiceField(choices=CaseBasis.choices, label="Основание")
    category = forms.CharField(max_length=200, required=False, label="Категория")
    description = forms.CharField(
        required=False,
        label="Описание",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    responsible_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).exclude(role="observer"),
        required=False,
        label="Ответственный",
        empty_label="— не назначен —",
    )

    def clean_iin_bin(self):
        value = self.cleaned_data["iin_bin"].strip()
        if not value.isdigit() or len(value) != 12:
            raise forms.ValidationError("ИИН/БИН должен содержать ровно 12 цифр.")
        return value


class TaxpayerImportForm(forms.Form):
    file = forms.FileField(
        label="Файл Excel (.xlsx)",
        widget=forms.FileInput(attrs={"accept": ".xlsx"}),
    )


class CaseFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=[("", "Все статусы")] + list(
            __import__("apps.cases.models", fromlist=["CaseStatus"]).CaseStatus.choices
        ),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label="Офис",
        empty_label="Все офисы",
    )
    region = forms.CharField(max_length=100, required=False, label="Регион")
    responsible_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        label="Ответственный",
        empty_label="Все",
    )
    date_from = forms.DateField(
        required=False,
        label="С",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label="По",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    search = forms.CharField(max_length=100, required=False, label="Поиск")
