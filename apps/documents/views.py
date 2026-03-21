import logging
import os
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, FormView

from apps.cases.models import AdministrativeCase, CaseStatus
from apps.cases.services import after_return_actions
from django.views import View
from .forms import DocumentCreateForm, NoticeForm
from .models import CaseDocument, DocumentStatus, DocumentType
from .services import create_new_version, generate_document, generate_notice

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
        if doc_type == DocumentType.NOTICE:
            return redirect("documents:notice_form", case_pk=self.case.pk)
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


class InspectionActCreateView(LoginRequiredMixin, FormView):
    """Генерация Акта налогового обследования. Доступна при статусе MAIL_RETURNED."""

    template_name = "documents/act_create.html"
    form_class = DocumentCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания документов.")
            return redirect("cases:list")

        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )

        if self.case.status != CaseStatus.MAIL_RETURNED:
            messages.error(
                request,
                "Акт обследования оформляется только после возврата почтового отправления."
            )
            return redirect("cases:detail", pk=self.case.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Фиксируем тип — пользователь не выбирает
        form.fields["doc_type"].initial = DocumentType.INSPECTION_ACT
        form.fields["doc_type"].choices = [(DocumentType.INSPECTION_ACT, "Акт налогового обследования")]
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        context["doc_type_display"] = "Акт налогового обследования"
        return context

    def form_valid(self, form):
        try:
            doc = generate_document(self.case, DocumentType.INSPECTION_ACT, self.request.user)
            after_return_actions(self.case, DocumentType.INSPECTION_ACT, self.request.user)
            messages.success(self.request, f"Акт {doc.doc_number} успешно оформлен.")
            return redirect("cases:detail", pk=self.case.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class DerRequestCreateView(LoginRequiredMixin, FormView):
    """Генерация Запроса в ДЭР. Доступна при статусе ACT_CREATED."""

    template_name = "documents/der_create.html"
    form_class = DocumentCreateForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "У вас нет прав для создания документов.")
            return redirect("cases:list")

        self.case = get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=kwargs["case_pk"],
        )

        if self.case.status != CaseStatus.ACT_CREATED:
            messages.error(
                request,
                "Запрос в ДЭР создаётся только после оформления акта обследования."
            )
            return redirect("cases:detail", pk=self.case.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["doc_type"].initial = DocumentType.DER_REQUEST
        form.fields["doc_type"].choices = [(DocumentType.DER_REQUEST, "Запрос в ДЭР об оказании содействия")]
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["case"] = self.case
        context["doc_type_display"] = "Запрос в ДЭР об оказании содействия"
        return context

    def form_valid(self, form):
        try:
            doc = generate_document(self.case, DocumentType.DER_REQUEST, self.request.user)
            after_return_actions(self.case, DocumentType.DER_REQUEST, self.request.user)
            messages.success(self.request, f"Запрос в ДЭР {doc.doc_number} успешно создан.")
            return redirect("cases:detail", pk=self.case.pk)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


class NoticeFormView(LoginRequiredMixin, View):
    """Интерактивная форма заполнения Извещения о явке."""
    template_name = "documents/notice_form.html"

    def _get_case(self, request, case_pk):
        return get_object_or_404(
            AdministrativeCase.objects.for_user(request.user),
            pk=case_pk,
        )

    def _build_context(self, case, form):
        from apps.cases.models import TaxAuthorityDetails
        details = TaxAuthorityDetails.get_singleton()
        responsible = case.responsible_user
        return {
            "case": case,
            "form": form,
            "auto_fields": {
                "Наименование органа": details.name or "—",
                "Налогоплательщик": f"{case.taxpayer.name} (БИН/ИИН: {case.taxpayer.iin_bin})",
                "Контактное лицо": responsible.get_full_name() if responsible else "—",
                "Телефон": responsible.phone if responsible else "—",
            },
        }

    def get(self, request, case_pk):
        from django.shortcuts import render
        from apps.cases.models import TaxAuthorityDetails
        case = self._get_case(request, case_pk)
        details = TaxAuthorityDetails.get_singleton()
        form = NoticeForm(initial={"hearing_address": details.address})
        return render(request, self.template_name, self._build_context(case, form))

    def post(self, request, case_pk):
        from django.shortcuts import render
        case = self._get_case(request, case_pk)
        form = NoticeForm(request.POST)
        if form.is_valid():
            try:
                doc = generate_notice(
                    case=case,
                    hearing_date=form.cleaned_data["hearing_date"],
                    hearing_time=form.cleaned_data["hearing_time"],
                    hearing_address=form.cleaned_data["hearing_address"],
                    user=request.user,
                )
                messages.success(request, f"Извещение {doc.doc_number} успешно сформировано.")
                return redirect("documents:detail", pk=doc.pk)
            except ValueError as e:
                messages.error(request, str(e))
        return render(request, self.template_name, self._build_context(case, form))


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
