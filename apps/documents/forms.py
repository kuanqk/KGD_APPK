from django import forms
from .models import DocumentType, DocumentTemplate


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
