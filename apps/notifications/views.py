import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView
from django.views import View

from .models import Notification
from .services import mark_read, mark_all_read

logger = logging.getLogger(__name__)


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return (
            Notification.objects
            .for_user(self.request.user)
            .select_related("case")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["unread_total"] = (
            Notification.objects.for_user(self.request.user).unread().count()
        )
        return context


class MarkReadView(LoginRequiredMixin, View):
    """POST /notifications/<pk>/read/ — пометить одно уведомление прочитанным."""

    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user,
        )
        mark_read(notification, request.user)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url:
            return redirect(next_url)
        if notification.url:
            return redirect(notification.url)
        return redirect("notifications:list")


class MarkAllReadView(LoginRequiredMixin, View):
    """POST /notifications/read-all/ — пометить все прочитанными."""

    def post(self, request):
        mark_all_read(request.user)
        return redirect("notifications:list")
