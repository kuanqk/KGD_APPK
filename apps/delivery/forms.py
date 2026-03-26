from django import forms
from .models import DeliveryMethod, DeliveryStatus


class DeliveryCreateForm(forms.Form):
    document_id = forms.IntegerField(widget=forms.HiddenInput)
    method = forms.ChoiceField(
        choices=DeliveryMethod.choices,
        label="Способ вручения",
        widget=forms.RadioSelect,
    )
    sent_at = forms.DateTimeField(
        required=False,
        label="Дата и время отправки",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    tracking_number = forms.CharField(
        max_length=100,
        required=False,
        label="Трек-номер",
        help_text="Обязателен для заказного письма",
        widget=forms.TextInput(attrs={"placeholder": "например, RU123456789KZ"}),
    )
    notes = forms.CharField(
        required=False,
        label="Примечание",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("method")
        tracking = cleaned.get("tracking_number", "").strip()
        if method == DeliveryMethod.REGISTERED_MAIL and not tracking:
            self.add_error("tracking_number", "Трек-номер обязателен для заказного письма.")
        return cleaned


class DeliveryResultForm(forms.Form):
    result_status = forms.ChoiceField(
        choices=[
            (DeliveryStatus.DELIVERED, "Вручено"),
            (DeliveryStatus.RETURNED, "Возвращено"),
        ],
        label="Результат",
        widget=forms.RadioSelect,
    )
    notes = forms.CharField(
        required=False,
        label="Примечание",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Укажите подробности..."}),
    )


class DeliveryFilterForm(forms.Form):
    status = forms.ChoiceField(
        required=False,
        label="Статус",
        choices=[("", "Все")] + list(
            __import__("apps.delivery.models", fromlist=["DeliveryStatus"]).DeliveryStatus.choices
        ),
    )
    method = forms.ChoiceField(
        required=False,
        label="Метод",
        choices=[("", "Все")] + list(DeliveryMethod.choices),
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
    search = forms.CharField(
        max_length=100,
        required=False,
        label="Поиск",
    )
