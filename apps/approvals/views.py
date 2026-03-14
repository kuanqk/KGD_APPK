import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, FormView

from .models import ApprovalFlow, ApprovalResult, EntityType
from .services import approve, reject, return_for_revision

logger = logging.getLogger(__name__)


class ApprovalQueueView(LoginRequiredMixin, ListView):
    template_name = "approvals/queue.html"
    context_object_name = "flows"
    paginate_by = 25

    def get_queryset(self):
        return (
            ApprovalFlow.objects
            .for_reviewer(self.request.user)
            .select_related("sent_by", "reviewed_by")
            .order_by("sent_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Статистика для заголовка
        context["total_pending"] = (
            ApprovalFlow.objects.for_reviewer(self.request.user).count()
        )
        return context


class ApprovalActionView(LoginRequiredMixin, FormView):
    """Обрабатывает approve / reject / return одним POST."""
    template_name = "approvals/action.html"

    # FormView без form_class — используем голый POST
    form_class = None

    def get_form(self, form_class=None):
        return None

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "reviewer"):
            messages.error(request, "Согласование доступно только руководителю.")
            return redirect("approvals:queue")

        self.flow = get_object_or_404(
            ApprovalFlow,
            pk=kwargs["pk"],
            result=ApprovalResult.PENDING,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["flow"] = self.flow
        context["entity"] = self._resolve_entity()
        context["history"] = ApprovalFlow.objects.for_entity(
            self.flow.entity_type, self.flow.entity_id
        )
        return context

    def _resolve_entity(self):
        if self.flow.entity_type == EntityType.DECISION:
            from apps.decisions.models import FinalDecision
            return FinalDecision.objects.select_related(
                "case", "case__taxpayer", "created_by"
            ).get(pk=self.flow.entity_id)
        return None

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        comment = request.POST.get("comment", "").strip()

        try:
            if action == "approve":
                approve(self.flow, request.user, comment)
                messages.success(request, "Решение утверждено.")
            elif action == "reject":
                if not comment:
                    messages.error(request, "Комментарий при отклонении обязателен.")
                    return self.get(request, *args, **kwargs)
                reject(self.flow, request.user, comment)
                messages.warning(request, "Решение отклонено.")
            elif action == "return":
                if not comment:
                    messages.error(request, "Комментарий при возврате обязателен.")
                    return self.get(request, *args, **kwargs)
                return_for_revision(self.flow, request.user, comment)
                messages.warning(request, "Возвращено на доработку.")
            else:
                messages.error(request, "Неизвестное действие.")
                return self.get(request, *args, **kwargs)
        except ValueError as e:
            messages.error(request, str(e))
            return self.get(request, *args, **kwargs)

        # Редирект к карточке сущности
        entity = self._resolve_entity()
        if entity and self.flow.entity_type == EntityType.DECISION:
            return redirect("decisions:detail", pk=entity.pk)
        return redirect("approvals:queue")
