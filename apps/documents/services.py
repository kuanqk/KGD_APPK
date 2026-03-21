import logging
import os
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.template import Context, Template

from apps.audit.services import audit_log
from .models import CaseDocument, DocumentStatus, DocumentTemplate, DocumentType

logger = logging.getLogger(__name__)

DOC_TYPE_PREFIX = {
    DocumentType.NOTICE: "ИЗВ",
    DocumentType.PRELIMINARY_DECISION: "ПРД",
    DocumentType.INSPECTION_ACT: "АКТ",
    DocumentType.DER_REQUEST: "ДЭР",
    DocumentType.HEARING_PROTOCOL: "ПРТ",
    DocumentType.TERMINATION_DECISION: "ПРК",
    DocumentType.AUDIT_INITIATION: "ВНП",
    DocumentType.AUDIT_ORDER: "ПРК",
}


def generate_doc_number(doc_type: str, case=None) -> str:
    """
    Генерирует номер документа формата <PREFIX>-<КОД>-<YYYYMMDD>-<NNNNNNN>.
    Если у дела нет подразделения — fallback на старый формат <PREFIX>-ГГГГ-NNNNN.
    """
    from django.db import transaction as db_transaction
    from apps.cases.models import Department

    prefix = DOC_TYPE_PREFIX.get(doc_type, "ДОК")
    today = date.today()
    year = today.year

    dept = getattr(case, "department", None) if case is not None else None

    if dept is None:
        # Fallback: старый формат для дел без подразделения
        full_prefix = f"{prefix}-{year}-"
        last = (
            CaseDocument.objects
            .filter(doc_number__startswith=full_prefix)
            .order_by("-doc_number")
            .values_list("doc_number", flat=True)
            .first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        return f"{full_prefix}{seq:05d}"

    dept_code = str(dept.code).zfill(2)
    date_str = today.strftime("%Y%m%d")

    with db_transaction.atomic():
        dept_obj = Department.objects.select_for_update().get(pk=dept.pk)
        if dept_obj.seq_year != year:
            dept_obj.seq_year = year
            dept_obj.doc_sequence = 1
        else:
            dept_obj.doc_sequence += 1
        dept_obj.save(update_fields=["doc_sequence", "seq_year"])
        seq = dept_obj.doc_sequence

    return f"{prefix}-{dept_code}-{date_str}-{seq:07d}"


def get_document_context(case) -> dict:
    """Формирует контекст подстановки для шаблона документа."""
    from apps.cases.models import TaxAuthorityDetails
    today = date.today()
    responsible = case.responsible_user
    details = TaxAuthorityDetails.get_singleton()
    return {
        "case_number": case.case_number,
        "case_basis": case.basis.name if case.basis else "",
        "case_region": case.region.name if case.region else "",
        "case_department": str(case.department) if case.department else "",
        "case_status": case.get_status_display(),
        "taxpayer_name": case.taxpayer.name,
        "taxpayer_iin": case.taxpayer.iin_bin,
        "taxpayer_type": case.taxpayer.get_taxpayer_type_display(),
        "taxpayer_address": case.taxpayer.address or "",
        "taxpayer_phone": case.taxpayer.phone or "",
        "taxpayer_email": case.taxpayer.email or "",
        "date_today": today.strftime("%d.%m.%Y"),
        "date_today_full": _format_date_full(today),
        "responsible_name": responsible.get_full_name() if responsible else "",
        "responsible_position": responsible.position.name if (responsible and responsible.position) else "",
        "responsible_phone": responsible.phone if responsible else "",
        "taxpayer_iin_bin": case.taxpayer.iin_bin,
        "authority_name": details.name,
        "authority_address": details.address,
        "deputy_name": details.deputy_name,
    }


def _format_date_full(d: date) -> str:
    months = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"{d.day} {months[d.month]} {d.year} года"


def _format_hearing_date(d: date) -> str:
    months = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    return f"«{d.day:02d}» {months[d.month]} {d.year}"


@transaction.atomic
def generate_notice(case, hearing_date, hearing_time, hearing_address: str, user) -> CaseDocument:
    """Генерирует Извещение о явке с указанными датой/временем/адресом заслушивания."""
    doc_type = DocumentType.NOTICE
    template = DocumentTemplate.objects.filter(doc_type=doc_type, is_active=True).first()
    if not template:
        raise ValueError("Активный шаблон «Извещение о явке» не найден.")

    context = get_document_context(case)
    context["authority_name"] = context.get("authority_name") or "______"
    responsible = case.responsible_user
    context["responsible_name"] = (
        (responsible.get_full_name() or responsible.username) if responsible else "______"
    )
    context["responsible_phone"] = responsible.phone if responsible else "______"
    context.update({
        "hearing_date": _format_hearing_date(hearing_date),
        "hearing_time": hearing_time.strftime("%H:%M"),
        "hearing_address": hearing_address,
    })
    context["doc_type_display"] = dict(DocumentType.choices).get(doc_type, doc_type)

    rendered_body = _render_template_body(template.body_template, context)

    from django.template.loader import render_to_string
    html_content = render_to_string(
        "documents/pdf/base.html",
        {"body": rendered_body, "context": context, "doc_type_display": context["doc_type_display"]},
    )

    pdf_bytes = _render_pdf(html_content)
    doc_number = generate_doc_number(doc_type, case)
    file_path = _save_pdf_file(doc_number, pdf_bytes)

    existing_count = CaseDocument.objects.filter(case=case, doc_type=doc_type).count()
    doc = CaseDocument.objects.create(
        case=case,
        template=template,
        doc_type=doc_type,
        doc_number=doc_number,
        version=existing_count + 1,
        status=DocumentStatus.GENERATED,
        file_path=file_path,
        created_by=user,
        metadata={
            "template_version": template.version,
            "context_snapshot": {k: v for k, v in context.items()},
        },
    )

    audit_log(
        user=user,
        action="notice_generated",
        entity_type="document",
        entity_id=doc.id,
        details={
            "doc_number": doc_number,
            "case_number": case.case_number,
            "hearing_date": str(hearing_date),
            "hearing_address": hearing_address,
        },
    )

    logger.info("Notice generated: %s for case %s by %s", doc_number, case.case_number, user)
    return doc


def _render_template_body(body_template: str, context: dict) -> str:
    """Рендерит строку шаблона через Django Template engine."""
    t = Template(body_template)
    return t.render(Context(context))


def _render_pdf(html_content: str) -> bytes:
    """Конвертирует HTML в PDF через xhtml2pdf. При ошибке — fallback на HTML."""
    from io import BytesIO
    try:
        from xhtml2pdf import pisa
        buffer = BytesIO()
        pisa.CreatePDF(html_content.encode("utf-8"), dest=buffer)
        return buffer.getvalue()
    except Exception as exc:
        logger.error("xhtml2pdf ошибка: %s", exc)
        return html_content.encode("utf-8")


def _save_pdf_file(doc_number: str, pdf_bytes: bytes) -> str:
    """Сохраняет PDF в media/documents/ГГГГ/ММ/ и возвращает относительный путь."""
    today = date.today()
    rel_dir = Path("documents") / str(today.year) / f"{today.month:02d}"
    abs_dir = Path(settings.MEDIA_ROOT) / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{doc_number}.pdf"
    abs_path = abs_dir / filename
    abs_path.write_bytes(pdf_bytes)

    return str(rel_dir / filename)


@transaction.atomic
def generate_document(case, doc_type: str, user) -> CaseDocument:
    """
    Генерирует документ для дела:
    1. Берёт активный шаблон нужного типа
    2. Рендерит HTML → PDF
    3. Сохраняет CaseDocument
    4. Пишет в AuditLog
    """
    from apps.cases.services import validate_document_date
    validate_document_date(case, date.today())

    template = DocumentTemplate.objects.filter(doc_type=doc_type, is_active=True).first()
    if not template:
        raise ValueError(f"Активный шаблон типа '{doc_type}' не найден.")

    context = get_document_context(case)
    context["doc_type_display"] = dict(DocumentType.choices).get(doc_type, doc_type)

    # Рендер тела шаблона
    rendered_body = _render_template_body(template.body_template, context)

    # Оборачиваем в PDF-шаблон
    from django.template.loader import render_to_string
    html_content = render_to_string(
        "documents/pdf/base.html",
        {"body": rendered_body, "context": context, "doc_type_display": context["doc_type_display"]},
    )

    pdf_bytes = _render_pdf(html_content)

    doc_number = generate_doc_number(doc_type, case)
    file_path = _save_pdf_file(doc_number, pdf_bytes)

    # Определяем версию (если уже есть документы того же типа по делу)
    existing_count = CaseDocument.objects.filter(case=case, doc_type=doc_type).count()
    version = existing_count + 1

    doc = CaseDocument.objects.create(
        case=case,
        template=template,
        doc_type=doc_type,
        doc_number=doc_number,
        version=version,
        status=DocumentStatus.GENERATED,
        file_path=file_path,
        created_by=user,
        metadata={
            "template_version": template.version,
            "context_snapshot": {k: v for k, v in context.items()},
        },
    )

    audit_log(
        user=user,
        action="document_generated",
        entity_type="document",
        entity_id=doc.id,
        details={
            "doc_number": doc_number,
            "doc_type": doc_type,
            "case_number": case.case_number,
            "version": version,
        },
    )

    logger.info("Document generated: %s for case %s by %s", doc_number, case.case_number, user)
    return doc


@transaction.atomic
def create_new_version(existing_doc: CaseDocument, user) -> CaseDocument:
    """
    Создаёт новую версию документа.
    Если старый подписан — отменяет его, создаёт новый.
    """
    case = existing_doc.case
    doc_type = existing_doc.doc_type

    if existing_doc.status == DocumentStatus.SIGNED:
        existing_doc.status = DocumentStatus.CANCELLED
        existing_doc.save(update_fields=["status"])

        audit_log(
            user=user,
            action="document_cancelled",
            entity_type="document",
            entity_id=existing_doc.id,
            details={"reason": "new_version_created", "doc_number": existing_doc.doc_number},
        )

    return generate_document(case, doc_type, user)


@transaction.atomic
def change_document_status(doc: CaseDocument, new_status: str, user) -> CaseDocument:
    """Меняет статус документа с аудитом."""
    old_status = doc.status
    doc.status = new_status
    doc.save(update_fields=["status"])

    audit_log(
        user=user,
        action="document_status_changed",
        entity_type="document",
        entity_id=doc.id,
        details={
            "doc_number": doc.doc_number,
            "from": old_status,
            "to": new_status,
        },
    )
    return doc
