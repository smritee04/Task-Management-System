import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View

from core.mixins import AdminRequiredMixin
from .forms import (
    TMSAuthenticationForm, AdminUserCreateForm, AdminUserUpdateForm,
    ProfileSelfUpdateForm,
)
from .models import User, AuditLog

audit_logger = logging.getLogger("tms.audit")


class TMSLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = TMSAuthenticationForm
    redirect_authenticated_user = True


class TMSLogoutView(LogoutView):
    next_page = "accounts:login"


@login_required
def post_login_redirect(request):
    """Single funnel that routes a freshly-authenticated user to their
    role's dashboard. Keeping this in one place avoids inconsistent
    role-to-URL mappings scattered across the codebase."""
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")
    if user.role == User.Role.SUPERVISOR:
        return redirect("accounts:supervisor_dashboard")
    return redirect("accounts:intern_dashboard")


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileSelfUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileSelfUpdateForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Critical: re-hash session so the user isn't logged out by
            # their own password change, while old sessions elsewhere
            # using the old password hash are invalidated.
            update_session_auth_hash(request, user)
            audit_logger.info("PASSWORD_CHANGED user=%s", user.username)
            messages.success(request, "Password changed successfully.")
            return redirect("accounts:profile")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, "accounts/change_password.html", {"form": form})


# ---------------------------------------------------------------------------
# Role dashboards (thin views; heavy lifting/queries live in tasks/reports apps
# and are wired in via each app's dashboard view - these are placeholders that
# the tasks app overrides with real querysets through template includes).
# ---------------------------------------------------------------------------

@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    from tasks.models import Task
    from accounts.models import User as U
    context = {
        "total_users": U.objects.count(),
        "total_interns": U.objects.filter(role=U.Role.INTERN).count(),
        "total_supervisors": U.objects.filter(role=U.Role.SUPERVISOR).count(),
        "total_tasks": Task.objects.count(),
        "tasks_pending": Task.objects.filter(status=Task.Status.PENDING).count(),
        "tasks_in_progress": Task.objects.filter(status=Task.Status.IN_PROGRESS).count(),
        "tasks_completed": Task.objects.filter(status=Task.Status.COMPLETED).count(),
        "recent_tasks": Task.objects.select_related("assigned_to", "created_by").order_by("-created_at")[:8],
    }
    return render(request, "accounts/admin_dashboard.html", context)


@login_required
def supervisor_dashboard(request):
    if not (request.user.is_superuser or request.user.role in (User.Role.SUPERVISOR, User.Role.ADMIN)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    from tasks.models import Task
    interns = User.objects.filter(supervisor=request.user)
    tasks = Task.objects.filter(assigned_to__in=interns).select_related("assigned_to")
    context = {
        "interns": interns,
        "tasks": tasks.order_by("-created_at")[:10],
        "pending_review": tasks.filter(status=Task.Status.COMPLETED, supervisor_approved=False).count(),
    }
    return render(request, "accounts/supervisor_dashboard.html", context)


@login_required
def intern_dashboard(request):
    if not (request.user.is_superuser or request.user.role in (User.Role.INTERN, User.Role.ADMIN)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    from tasks.models import Task
    my_tasks = Task.objects.filter(assigned_to=request.user)
    context = {
        "my_tasks": my_tasks.order_by("-deadline")[:10],
        "pending_count": my_tasks.filter(status=Task.Status.PENDING).count(),
        "in_progress_count": my_tasks.filter(status=Task.Status.IN_PROGRESS).count(),
        "completed_count": my_tasks.filter(status=Task.Status.COMPLETED).count(),
    }
    return render(request, "accounts/intern_dashboard.html", context)


# ---------------------------------------------------------------------------
# Admin: user management (create/list/update/deactivate)
# ---------------------------------------------------------------------------

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.all().order_by("role", "username")
        q = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "").strip()
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
        if role in dict(User.Role.choices):
            qs = qs.filter(role=role)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["roles"] = User.Role.choices
        ctx["query"] = self.request.GET.get("q", "")
        ctx["selected_role"] = self.request.GET.get("role", "")
        return ctx


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = "accounts/user_detail.html"
    context_object_name = "profile_user"


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = AdminUserCreateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLog.objects.create(
            actor=self.request.user, target_user=self.object,
            action="USER_CREATED", detail=f"role={self.object.role}",
        )
        audit_logger.info(
            "USER_CREATED actor=%s target=%s role=%s",
            self.request.user.username, self.object.username, self.object.role,
        )
        messages.success(self.request, f"User '{self.object.username}' created.")
        return response


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = AdminUserUpdateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        was_active = User.objects.get(pk=self.object.pk).is_active
        response = super().form_valid(form)
        if was_active and not self.object.is_active:
            AuditLog.objects.create(
                actor=self.request.user, target_user=self.object, action="USER_DEACTIVATED",
            )
            audit_logger.warning(
                "USER_DEACTIVATED actor=%s target=%s", self.request.user.username, self.object.username
            )
        messages.success(self.request, f"User '{self.object.username}' updated.")
        return response


class UserDeleteView(AdminRequiredMixin, View):
    """
    Deletion is a deliberately separate, POST-only view (never a GET link)
    to avoid CSRF-via-link and accidental-crawler deletion classes of bugs.
    Admins cannot delete themselves, preventing accidental lockout.
    """

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target.pk == request.user.pk:
            messages.error(request, "You cannot delete your own account.")
            return redirect("accounts:user_list")
        username = target.username
        AuditLog.objects.create(
            actor=request.user, target_user=None, action="USER_DELETED", detail=f"username={username}"
        )
        audit_logger.warning("USER_DELETED actor=%s target=%s", request.user.username, username)
        target.delete()
        messages.success(request, f"User '{username}' deleted.")
        return redirect("accounts:user_list")
