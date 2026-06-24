"""
Custom user model with role-based access control.

Using a custom AUTH_USER_MODEL from day one (rather than Django's default
User + a bolted-on Profile) keeps role checks in one place and avoids the
classic "profile doesn't exist yet" bug that creates a security gap.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class Domain(models.Model):
    """
    A subject area interns work within (e.g. "Web Development", "Data
    Science", "UI/UX Design"). Replaces the old free-text department field
    with a proper lookup so domains stay consistent and reportable.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

#Abstractuser django built in user class
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        SUPERVISOR = "supervisor", "Supervisor"
        INTERN = "intern", "Intern"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.INTERN)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    # An intern belongs to exactly one domain (kept simple & explicit, same
    # pattern as `supervisor` below). Only meaningful when role == INTERN.
    domain = models.ForeignKey(
        Domain,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="interns",
    )

    # An intern is mentored by exactly one supervisor (kept simple & explicit).
    # Only meaningful when role == INTERN.
    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"role": "supervisor"},
        related_name="interns",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def get_absolute_url(self):
        return reverse("accounts:user_detail", kwargs={"pk": self.pk})

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_supervisor_role(self):
        return self.role == self.Role.SUPERVISOR

    @property
    def is_intern_role(self):
        return self.role == self.Role.INTERN


class AuditLog(models.Model):
    """
    Append-only record of security-relevant account actions
    (created/deactivated/role-changed/password-reset, etc.).
    Never edited or deleted through the app - only ever appended to.
    """
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="audit_actions"
    )
    target_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="audit_targeted", blank=True
    )
    action = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor}: {self.action}"
