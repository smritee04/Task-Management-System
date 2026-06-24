from django import forms
from django.utils import timezone

from accounts.models import User
from .models import Task, ProgressUpdate, Project


class StyledFormMixin:
    def _style_fields(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control").strip()


class ProjectForm(StyledFormMixin, forms.ModelForm):
    """Used by admins and supervisors to create/manage projects."""

    class Meta:
        model = Project
        fields = ["name", "description", "status", "start_date", "deadline"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class TaskForm(StyledFormMixin, forms.ModelForm):
    """
    Used by admins (and supervisors, who may only assign within their own
    interns - enforced in the view, not just the form, since forms alone
    are not a security boundary).
    """

    class Meta:
        model = Task
        fields = ["project", "title", "description", "assigned_to", "priority", "deadline"]
        widgets = {
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, assignable_interns=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        qs = assignable_interns if assignable_interns is not None else User.objects.filter(role=User.Role.INTERN)
        self.fields["assigned_to"].queryset = qs
        self.fields["project"].queryset = Project.objects.all()
        self.fields["project"].required = False

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline < timezone.now():
            raise forms.ValidationError("Deadline cannot be in the past.")
        return deadline


class ProgressUpdateForm(StyledFormMixin, forms.ModelForm):
    """Interns use this to report progress on their own tasks only."""

    class Meta:
        model = ProgressUpdate
        fields = ["note", "progress_percent", "new_status"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
