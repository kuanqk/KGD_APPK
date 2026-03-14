import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)


class AppkLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class AppkLogoutView(LogoutView):
    next_page = "accounts:login"


class AppkPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change.html"
    success_url = reverse_lazy("accounts:dashboard")


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context
