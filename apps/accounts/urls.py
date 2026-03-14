from django.urls import path
from .views import AppkLoginView, AppkLogoutView, AppkPasswordChangeView, DashboardView

app_name = "accounts"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", AppkLoginView.as_view(), name="login"),
    path("logout/", AppkLogoutView.as_view(), name="logout"),
    path("password-change/", AppkPasswordChangeView.as_view(), name="password_change"),
]
