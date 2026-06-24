"""
Forms for authentication and user management.

All forms here run Django's full validation pipeline (including
AUTH_PASSWORD_VALIDATORS) - there is no path in the UI that creates or
modifies a user while bypassing validation.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User


class StyledFormMixin:
    """Adds a consistent CSS class to every field widget except checkboxes,
    which the theme styles differently (inline, not as a block input)."""
    def _style_fields(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control").strip()


class TMSAuthenticationForm(StyledFormMixin, AuthenticationForm):
    """Login form. Deliberately gives no hint whether the username or the
    password was wrong (prevents username enumeration)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    error_messages = {
        "invalid_login": "Please enter a correct username and password.",
        "inactive": "This account is inactive. Contact an administrator.",
    }


class AdminUserCreateForm(StyledFormMixin, UserCreationForm):
    """Used only by admins to provision new accounts."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "role", "domain", "phone_number", "supervisor",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        self.fields["supervisor"].queryset = User.objects.filter(role=User.Role.SUPERVISOR)
        self.fields["supervisor"].required = False
        self.fields["domain"].required = False

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not email:
            raise ValidationError("Email is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        supervisor = cleaned.get("supervisor")
        domain = cleaned.get("domain")
        if role == User.Role.INTERN and supervisor is None:
            self.add_error("supervisor", "Interns must be assigned a supervisor.")
        if role == User.Role.INTERN and domain is None:
            self.add_error("domain", "Interns must be assigned a domain.")
        if role != User.Role.INTERN and supervisor is not None:
            # Only interns carry a supervisor link; silently clear instead of erroring.
            cleaned["supervisor"] = None
        if role != User.Role.INTERN and domain is not None:
            # Only interns belong to a domain; silently clear instead of erroring.
            cleaned["domain"] = None
        return cleaned


class AdminUserUpdateForm(StyledFormMixin, forms.ModelForm):
    """Edit an existing user's profile/role. Never touches the password."""

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email", "role",
            "domain", "phone_number", "supervisor", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        self.fields["supervisor"].queryset = User.objects.filter(role=User.Role.SUPERVISOR)
        self.fields["supervisor"].required = False
        self.fields["domain"].required = False

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        domain = cleaned.get("domain")
        if role == User.Role.INTERN and domain is None:
            self.add_error("domain", "Interns must be assigned a domain.")
        if role != User.Role.INTERN and domain is not None:
            cleaned["domain"] = None
        return cleaned


class ProfileSelfUpdateForm(StyledFormMixin, forms.ModelForm):
    """
    What a logged-in user may edit about themselves. Deliberately excludes
    `role`, `is_active`, `is_staff`, `is_superuser`, and `supervisor` - a
    user can never grant themselves elevated privileges through this form.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "profile_photo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with this email already exists.")
        return email
