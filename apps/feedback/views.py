import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from apps.audit.services import audit_log
from .models import Feedback, FeedbackType

logger = logging.getLogger(__name__)


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

        feedback = Feedback.objects.create(
            user=request.user,
            feedback_type=feedback_type,
            description=description,
            case_number=case_number,
            attachment=attachment,
        )

        audit_log(
            user=request.user,
            action="feedback_created",
            entity_type="feedback",
            entity_id=feedback.id,
            details={"type": feedback_type},
        )

        return JsonResponse({"success": True})


class FeedbackListView(LoginRequiredMixin, ListView):
    model = Feedback
    template_name = "feedback/list.html"
    context_object_name = "feedbacks"
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != "admin":
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = Feedback.objects.select_related("user").order_by("-created_at")
        type_filter = self.request.GET.get("type", "")
        reviewed_filter = self.request.GET.get("is_reviewed", "")
        if type_filter:
            qs = qs.filter(feedback_type=type_filter)
        if reviewed_filter == "0":
            qs = qs.filter(is_reviewed=False)
        elif reviewed_filter == "1":
            qs = qs.filter(is_reviewed=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["feedback_types"] = FeedbackType.choices
        ctx["type_filter"] = self.request.GET.get("type", "")
        ctx["reviewed_filter"] = self.request.GET.get("is_reviewed", "")
        ctx["unreviewed_count"] = Feedback.objects.filter(is_reviewed=False).count()
        return ctx


class FeedbackMarkReviewedView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if request.user.role != "admin":
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()
        feedback = get_object_or_404(Feedback, pk=pk)
        feedback.is_reviewed = True
        feedback.save(update_fields=["is_reviewed"])
        audit_log(
            user=request.user,
            action="feedback_reviewed",
            entity_type="feedback",
            entity_id=feedback.id,
            details={},
        )
        return redirect("feedback:list")
