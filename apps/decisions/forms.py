from django import forms
from .models import TerminationBasis


class TerminationCreateForm(forms.Form):
    basis = forms.ChoiceField(
        choices=TerminationBasis.choices,
        label="Основание прекращения",
        widget=forms.RadioSelect,
    )
    comment = forms.CharField(
        label="Обоснование",
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "Подробно опишите основание для прекращения дела...",
        }),
    )


class TaxAuditCreateForm(forms.Form):
    comment = forms.CharField(
        label="Обоснование назначения проверки",
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "Укажите основания и предмет внеплановой проверки...",
        }),
    )


class DecisionReviewForm(forms.Form):
    ACTION_CHOICES = [
        ("approve", "Утвердить"),
        ("reject", "Отклонить"),
    ]
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Решение",
        widget=forms.RadioSelect,
    )
    rejection_comment = forms.CharField(
        label="Комментарий при отклонении",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Обязателен при отклонении...",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get("action")
        comment = cleaned.get("rejection_comment", "").strip()
        if action == "reject" and not comment:
            self.add_error("rejection_comment", "Комментарий обязателен при отклонении.")
        return cleaned
