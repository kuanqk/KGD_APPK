from django import forms
from apps.accounts.models import User
from .models import AdministrativeCase, Department, Taxpayer, TaxpayerType, Region, CaseBasis, CaseCategory, TaxAuthorityDetails
from .validators import KZValidator, IIN_BIN_ERRORS, PHONE_ERRORS


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
    taxpayer_type = forms.ChoiceField(
        choices=TaxpayerType.choices,
        label="Тип НП",
        widget=forms.Select(attrs={"readonly": "true"}),
    )
    taxpayer_address = forms.CharField(
        required=False,
        label="Адрес НП",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    taxpayer_phone = forms.CharField(max_length=30, required=False, label="Телефон НП")
    taxpayer_email = forms.EmailField(required=False, label="Email НП")

    # Данные дела
    region = forms.ModelChoiceField(
        queryset=Region.objects.filter(is_active=True),
        label="Регион",
        empty_label="— выберите регион —",
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        label="Подразделение",
        empty_label="— выберите подразделение —",
    )
    basis = forms.ModelMultipleChoiceField(
        queryset=CaseBasis.objects.filter(is_active=True),
        label="Основание",
        required=True,
        widget=forms.CheckboxSelectMultiple,
    )
    category = forms.ModelMultipleChoiceField(
        queryset=CaseCategory.objects.filter(is_active=True),
        label="Категория",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
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
        result = KZValidator.validate_iin_bin(value)
        if not result.valid:
            raise forms.ValidationError(
                IIN_BIN_ERRORS.get(result.error, "Неверный ИИН/БИН.")
            )
        self._iin_bin_result = result
        return value

    def clean_taxpayer_phone(self):
        value = self.cleaned_data.get("taxpayer_phone", "").strip()
        if not value:
            return value
        result = KZValidator.validate_phone(value)
        if not result.valid:
            raise forms.ValidationError(
                PHONE_ERRORS.get(result.error, "Неверный номер телефона.")
            )
        return result.value  # нормализованный +7XXXXXXXXXX

    def clean(self):
        cleaned = super().clean()
        if hasattr(self, "_iin_bin_result"):
            cleaned["taxpayer_type"] = (
                "individual" if self._iin_bin_result.type == "IIN" else "legal"
            )
        return cleaned


class TaxAuthorityDetailsForm(forms.ModelForm):
    class Meta:
        model = TaxAuthorityDetails
        fields = [
            "department", "name", "bin_number", "address", "city",
            "phone", "deputy_name", "deputy_position", "is_active",
        ]
        widgets = {
            "department": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "bin_number": forms.TextInput(attrs={"class": "form-control", "maxlength": 12}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "deputy_name": forms.TextInput(attrs={"class": "form-control"}),
            "deputy_position": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


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
