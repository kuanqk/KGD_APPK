from django import forms
from apps.accounts.models import User
from .models import AdministrativeCase, Department, Taxpayer, CaseBasis, TaxpayerType
from .validators import validate_iin_bin


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

    _IIN_BIN_ERRORS = {
        "invalid_format": "ИИН/БИН должен содержать 12 цифр.",
        "invalid_checksum": "Неверная контрольная сумма ИИН/БИН.",
        "invalid_birthdate": "Некорректная дата рождения в ИИН.",
        "invalid_registration_date": "Некорректная дата регистрации в БИН.",
        "unknown_type": "Не удалось определить тип ИИН/БИН.",
    }

    def clean_iin_bin(self):
        value = self.cleaned_data["iin_bin"].strip()
        valid, result = validate_iin_bin(value)
        if not valid:
            raise forms.ValidationError(
                self._IIN_BIN_ERRORS.get(result, "Неверный ИИН/БИН.")
            )
        # Сохраняем определённый тип для использования в clean()
        self._iin_bin_type = result
        return value

    def clean(self):
        cleaned = super().clean()
        # Автоматически устанавливаем тип НП по результату валидации ИИН/БИН
        if hasattr(self, "_iin_bin_type"):
            cleaned["taxpayer_type"] = "individual" if self._iin_bin_type == "IIN" else "legal"
        return cleaned


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
