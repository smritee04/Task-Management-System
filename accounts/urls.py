from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.TMSLoginView.as_view(), name="login"),
    path("logout/", views.TMSLogoutView.as_view(), name="logout"),
    path("redirect/", views.post_login_redirect, name="post_login_redirect"),

    path("profile/", views.profile_view, name="profile"),
    path("profile/password/", views.change_password_view, name="change_password"),

    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("dashboard/supervisor/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path("dashboard/intern/", views.intern_dashboard, name="intern_dashboard"),

    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/new/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_update"),
    path("users/<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
]
