import logging
import os
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView

from apps.cases.models import AdministrativeCase
from .forms import DocumentCreateForm
from .models import CaseDocument, DocumentStatus
from .services import create_new_version, generate_document

logger = logging.getLogger(__name__)


class DocumentCreateView(LoginRequiredMixin, FormView):
    template_name = "documents/create.html"
    form_class = DocumentCreateForm

    def dispatch(self, request, *args, **kwargs):
        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания документов.")
            return redirect("cases:detail", pk=self.case.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        return context

    def form_valid(self, form):
        doc_type = form.cleaned_data["doc_type"]
        try:
            doc = generate_document(self.case, doc_type, self.request.user)
            messages.success(self.request, f"Документ {doc.doc_number} успешно сформирован.")
            return redirect("documents:detail", pk=doc.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class DocumentDetailView(LoginRequiredMixin, DetailView):
    template_name = "documents/detail.html"
    context_object_name = "doc"

    def get_queryset(self):
        return CaseDocument.objects.for_user(self.request.user).select_related(
            "case", "case__taxpayer", "template", "created_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create_new_version"] = (
            self.object.status == DocumentStatus.SIGNED
            and self.request.user.role in ("admin", "operator")
        )
        context["can_delete"] = (
            self.object.is_deletable
            and self.request.user.role in ("admin", "operator")
        )
        return context

    def post(self, request, *args, **kwargs):
        doc = self.get_object()
        action = request.POST.get("action")

        if action == "new_version":
            if doc.status != DocumentStatus.SIGNED:
                messages.error(request, "Новая версия создаётся только для подписанных документов.")
                return redirect("documents:detail", pk=doc.pk)
            new_doc = create_new_version(doc, request.user)
            messages.success(request, f"Создана новая версия: {new_doc.doc_number}.")
            return redirect("documents:detail", pk=new_doc.pk)

        messages.error(request, "Неизвестное действие.")
        return redirect("documents:detail", pk=doc.pk)


def document_download(request, pk):
    if not request.user.is_authenticated:
        raise Http404

    doc = get_object_or_404(
        CaseDocument.objects.for_user(request.user),
        pk=pk,
    )
    if not doc.file_path:
        raise Http404("Файл документа не найден.")

    from django.conf import settings
    abs_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
    if not os.path.exists(abs_path):
        raise Http404("Файл документа не найден на диске.")

    filename = f"{doc.doc_number}.pdf"
    return FileResponse(
        open(abs_path, "rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )
