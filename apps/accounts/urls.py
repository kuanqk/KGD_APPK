from django.urls import path
from .views import (
    AppkLoginView, AppkLogoutView, AppkPasswordChangeView, DashboardView,
    UserListView, UserCreateView, UserUpdateView, UserDeactivateView,
)

app_name = "accounts"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("login/", AppkLoginView.as_view(), name="login"),
    path("logout/", AppkLogoutView.as_view(), name="logout"),
    path("password-change/", AppkPasswordChangeView.as_view(), name="password_change"),
    # Admin: user management
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/create/", UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/deactivate/", UserDeactivateView.as_view(), name="user_deactivate"),
]
