import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView, CreateView, UpdateView
from django_ratelimit.decorators import ratelimit

from apps.audit.services import audit_log
from .forms import UserCreateForm, UserUpdateForm
from .models import User

logger = logging.getLogger(__name__)


class AdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or (
            request.user.role != "admin" and not request.user.is_superuser
        ):
            raise Http404
        return super().dispatch(request, *args, **kwargs)


# ─── Auth views ───────────────────────────────────────────────────────────────

@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=False), name="dispatch")
class AppkLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return HttpResponse(
                "Слишком много попыток входа. Подождите минуту и попробуйте снова.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )
        return super().dispatch(request, *args, **kwargs)


class AppkLogoutView(LogoutView):
    next_page = "accounts:login"


class AppkPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change.html"
    success_url = reverse_lazy("accounts:dashboard")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        from apps.cases.services import get_dashboard_data
        context = super().get_context_data(**kwargs)
        context.update(get_dashboard_data(self.request.user))
        return context


# ─── User management (admin only) ─────────────────────────────────────────────

class UserListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 30

    def get_queryset(self):
        qs = User.objects.order_by("last_name", "first_name", "username")
        q = self.request.GET.get("q", "").strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(username__icontains=q) | Q(first_name__icontains=q)
                | Q(last_name__icontains=q) | Q(email__icontains=q)
            )
        role = self.request.GET.get("role", "")
        if role:
            qs = qs.filter(role=role)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import UserRole
        context["roles"] = UserRole.choices
        context["q"] = self.request.GET.get("q", "")
        context["role_filter"] = self.request.GET.get("role", "")
        return context


class UserCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        user = form.save()
        audit_log(
            user=self.request.user,
            action="user_created",
            entity_type="user",
            entity_id=user.id,
            details={"username": user.username, "role": user.role},
        )
        messages.success(self.request, f"Пользователь «{user.username}» создан.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = "Создать пользователя"
        return context


class UserUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        old_role = User.objects.get(pk=self.object.pk).role
        user = form.save()
        changes = {}
        if old_role != user.role:
            changes["role"] = {"from": old_role, "to": user.role}
        audit_log(
            user=self.request.user,
            action="user_updated",
            entity_type="user",
            entity_id=user.id,
            details={"username": user.username, **changes},
        )
        messages.success(self.request, f"Пользователь «{user.username}» обновлён.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = f"Редактировать: {self.object}"
        return context


class UserDeactivateView(AdminRequiredMixin, LoginRequiredMixin, View):
    """POST /accounts/users/<pk>/deactivate/ — деактивация (не удаление)."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if user == request.user:
            messages.error(request, "Нельзя деактивировать собственную учётную запись.")
            return redirect("accounts:user_list")

        was_active = user.is_active
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])

        action = "user_activated" if user.is_active else "user_deactivated"
        audit_log(
            user=request.user,
            action=action,
            entity_type="user",
            entity_id=user.id,
            details={"username": user.username, "is_active": user.is_active},
        )
        status = "активирован" if user.is_active else "деактивирован"
        messages.success(request, f"Пользователь «{user.username}» {status}.")
        return redirect("accounts:user_list")
