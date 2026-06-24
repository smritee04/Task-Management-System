"""
Reusable access-control mixins.

These are the single source of truth for "who is allowed to see/do what".
Every view that needs role restriction should use one of these instead of
re-implementing role checks ad hoc - that consistency is what prevents
authorization loopholes from creeping in view-by-view.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

audit_logger = logging.getLogger("tms.audit")


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Base mixin: restricts a class-based view to users whose `.role`
    is in `allowed_roles`. Superusers (Django admin) always pass.
    Subclasses must set `allowed_roles = {"admin", "supervisor", "intern"}`.
    """
    allowed_roles = frozenset()
    raise_exception = True  # 403 instead of redirect-to-login loop for authenticated-but-wrong-role users

    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        allowed = user.role in self.allowed_roles
        if not allowed:
            audit_logger.warning(
                "Access denied: user=%s role=%s tried to access %s",
                user.username, user.role, self.request.path,
            )
        return allowed

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("You do not have permission to access this page.")


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = frozenset({"admin"})


class SupervisorRequiredMixin(RoleRequiredMixin):
    allowed_roles = frozenset({"admin", "supervisor"})


class InternRequiredMixin(RoleRequiredMixin):
    allowed_roles = frozenset({"admin", "intern"})


class AnyStaffRequiredMixin(RoleRequiredMixin):
    """Admins and supervisors - i.e. anyone who isn't a plain intern."""
    allowed_roles = frozenset({"admin", "supervisor"})


def user_is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == "admin")


def user_is_supervisor(user):
    return user.is_authenticated and (user.is_superuser or user.role == "supervisor")


def user_is_intern(user):
    return user.is_authenticated and (user.is_superuser or user.role == "intern")
