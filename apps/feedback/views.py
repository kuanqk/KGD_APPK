import csv
import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from apps.audit.services import audit_log
from .models import Feedback, FeedbackPriority, FeedbackStatus, FeedbackType

logger = logging.getLogger(__name__)


def _require_admin(request):
    return request.user.is_authenticated and request.user.role == "admin"


def _can_view_feedback(request):
    """Список, детализация, статистика, CSV — для администраторов и руководителей."""
    return request.user.is_authenticated and request.user.role in ("admin", "reviewer")


class FeedbackCreateView(LoginRequiredMixin, View):
    def post(self, request):
        feedback_type = request.POST.get("feedback_type", "").strip()
        description = request.POST.get("description", "").strip()
        case_number = request.POST.get("case_number", "").strip()
        attachment = request.FILES.get("attachment")

        if not description:
            return JsonResponse({"success": False, "error": "Описание обязательно."}, status=400)

        if feedback_type not in FeedbackType.values:
            return JsonResponse({"success": False, "error": "Неверный тип отзыва."}, status=400)

        page_url = request.POST.get("page_url", "")[:500]
        page_title = request.POST.get("page_title", "")[:300]
        user_agent_str = request.META.get("HTTP_USER_AGENT", "")[:500]
        try:
            context_data = json.loads(request.POST.get("context_json", "{}") or "{}")
            if not isinstance(context_data, dict):
                context_data = {}
        except (json.JSONDecodeError, ValueError):
            context_data = {}

        feedback = Feedback.objects.create(
            user=request.user,
            feedback_type=feedback_type,
            description=description,
            case_number=case_number,
            attachment=attachment,
            page_url=page_url,
            page_title=page_title,
            user_agent=user_agent_str,
            context=context_data,
        )

        audit_log(
            user=request.user,
            action="feedback_created",
            entity_type="feedback",
            entity_id=feedback.id,
            details={"type": feedback_type, "page_url": page_url},
        )

        return JsonResponse({"success": True})


class FeedbackListView(LoginRequiredMixin, ListView):
    model = Feedback
    template_name = "feedback/list.html"
    context_object_name = "feedbacks"
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not _can_view_feedback(request):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Feedback.objects.select_related("user").order_by("-created_at")
        if t := self.request.GET.get("type", ""):
            qs = qs.filter(feedback_type=t)
        if s := self.request.GET.get("status", ""):
            qs = qs.filter(status=s)
        if p := self.request.GET.get("priority", ""):
            qs = qs.filter(priority=p)
        if q := self.request.GET.get("q", "").strip():
            qs = qs.filter(
                Q(description__icontains=q)
                | Q(case_number__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__first_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["feedback_types"] = FeedbackType.choices
        ctx["feedback_statuses"] = FeedbackStatus.choices
        ctx["feedback_priorities"] = FeedbackPriority.choices
        ctx["type_filter"] = self.request.GET.get("type", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        ctx["priority_filter"] = self.request.GET.get("priority", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["unreviewed_count"] = Feedback.objects.filter(is_reviewed=False).count()
        return ctx


class FeedbackDetailView(LoginRequiredMixin, DetailView):
    model = Feedback
    template_name = "feedback/detail.html"
    context_object_name = "fb"

    def dispatch(self, request, *args, **kwargs):
        if not _can_view_feedback(request):
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["feedback_statuses"] = FeedbackStatus.choices
        ctx["feedback_priorities"] = FeedbackPriority.choices
        ctx["can_manage_feedback"] = _require_admin(self.request)
        return ctx


class FeedbackUpdateView(LoginRequiredMixin, View):
    """Обновить статус, приоритет и комментарий администратора."""

    def post(self, request, pk):
        if not _require_admin(request):
            return HttpResponseForbidden()
        feedback = get_object_or_404(Feedback, pk=pk)

        new_status = request.POST.get("status", "").strip()
        new_priority = request.POST.get("priority", "").strip()
        admin_comment = request.POST.get("admin_comment", "").strip()

        update_fields = []

        if new_status and new_status in FeedbackStatus.values:
            feedback.status = new_status
            update_fields.append("status")
            if new_status in (FeedbackStatus.RESOLVED, FeedbackStatus.REJECTED):
                feedback.is_reviewed = True
                feedback.resolved_at = timezone.now()
                update_fields += ["is_reviewed", "resolved_at"]
            elif new_status == FeedbackStatus.NEW:
                feedback.is_reviewed = False
                feedback.resolved_at = None
                update_fields += ["is_reviewed", "resolved_at"]

        if new_priority and new_priority in FeedbackPriority.values:
            feedback.priority = new_priority
            update_fields.append("priority")

        if "admin_comment" in request.POST:
            feedback.admin_comment = admin_comment
            update_fields.append("admin_comment")

        if update_fields:
            feedback.save(update_fields=update_fields)
            audit_log(
                user=request.user,
                action="feedback_updated",
                entity_type="feedback",
                entity_id=feedback.id,
                details={"status": feedback.status, "priority": feedback.priority},
            )

        next_url = request.POST.get("next", "")
        if next_url == "detail":
            return redirect("feedback:detail", pk=pk)
        return redirect("feedback:list")


class FeedbackMarkReviewedView(LoginRequiredMixin, View):
    """Оставлен для обратной совместимости — теперь делегирует в FeedbackUpdateView."""

    def post(self, request, pk):
        if not _require_admin(request):
            return HttpResponseForbidden()
        feedback = get_object_or_404(Feedback, pk=pk)
        feedback.resolve()
        feedback.save(update_fields=["status", "is_reviewed", "resolved_at"])
        audit_log(
            user=request.user,
            action="feedback_reviewed",
            entity_type="feedback",
            entity_id=feedback.id,
            details={},
        )
        return redirect("feedback:list")


class FeedbackExportCsvView(LoginRequiredMixin, View):
    def get(self, request):
        if not _can_view_feedback(request):
            return HttpResponseForbidden()

        qs = Feedback.objects.select_related("user").order_by("-created_at")
        if t := request.GET.get("type", ""):
            qs = qs.filter(feedback_type=t)
        if s := request.GET.get("status", ""):
            qs = qs.filter(status=s)
        if p := request.GET.get("priority", ""):
            qs = qs.filter(priority=p)
        if q := request.GET.get("q", "").strip():
            qs = qs.filter(
                Q(description__icontains=q)
                | Q(case_number__icontains=q)
                | Q(user__last_name__icontains=q)
            )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="feedback.csv"'
        response.write("\ufeff")  # BOM для Excel

        writer = csv.writer(response)
        writer.writerow([
            "ID", "Дата", "Пользователь", "Роль", "Тип",
            "Статус", "Приоритет", "Номер дела", "Описание",
            "Комментарий администратора", "Дата закрытия",
        ])
        for fb in qs:
            writer.writerow([
                fb.pk,
                fb.created_at.strftime("%d.%m.%Y %H:%M"),
                fb.user.get_full_name() if fb.user else "",
                fb.user.get_role_display() if fb.user else "",
                fb.get_feedback_type_display(),
                fb.get_status_display(),
                fb.get_priority_display(),
                fb.case_number,
                fb.description,
                fb.admin_comment,
                fb.resolved_at.strftime("%d.%m.%Y %H:%M") if fb.resolved_at else "",
            ])
        return response


class FeedbackStatsView(LoginRequiredMixin, View):
    def get(self, request):
        if not _can_view_feedback(request):
            return HttpResponseForbidden()

        by_type = (
            Feedback.objects.values("feedback_type")
            .annotate(cnt=Count("id"))
            .order_by("feedback_type")
        )
        by_status = (
            Feedback.objects.values("status")
            .annotate(cnt=Count("id"))
            .order_by("status")
        )
        by_priority = (
            Feedback.objects.values("priority")
            .annotate(cnt=Count("id"))
            .order_by("priority")
        )
        weekly = (
            Feedback.objects.annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(cnt=Count("id"))
            .order_by("week")
        )

        type_labels = [dict(FeedbackType.choices).get(r["feedback_type"], r["feedback_type"]) for r in by_type]
        type_data = [r["cnt"] for r in by_type]

        status_labels = [dict(FeedbackStatus.choices).get(r["status"], r["status"]) for r in by_status]
        status_data = [r["cnt"] for r in by_status]

        priority_labels = [dict(FeedbackPriority.choices).get(r["priority"], r["priority"]) for r in by_priority]
        priority_data = [r["cnt"] for r in by_priority]

        week_labels = [r["week"].strftime("%d.%m") if r["week"] else "" for r in weekly]
        week_data = [r["cnt"] for r in weekly]

        ctx = {
            "total": Feedback.objects.count(),
            "open_count": Feedback.objects.filter(status__in=[FeedbackStatus.NEW, FeedbackStatus.IN_PROGRESS]).count(),
            "resolved_count": Feedback.objects.filter(status=FeedbackStatus.RESOLVED).count(),
            "type_labels": type_labels,
            "type_data": type_data,
            "status_labels": status_labels,
            "status_data": status_data,
            "priority_labels": priority_labels,
            "priority_data": priority_data,
            "week_labels": week_labels,
            "week_data": week_data,
        }
        return render(request, "feedback/stats.html", ctx)
