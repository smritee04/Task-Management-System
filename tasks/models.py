from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Project(models.Model):
    """A body of work that groups related tasks together."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="projects_created",
    )

    start_date = models.DateField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tasks:project_detail", kwargs={"pk": self.pk})

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def completed_task_count(self):
        return self.tasks.filter(status=Task.Status.COMPLETED).count() if self.pk else 0


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="tasks_created",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="tasks_assigned", limit_choices_to={"role": "intern"},
    )

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    progress_percent = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    deadline = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    # A supervisor must explicitly approve before a task is considered
    # fully closed out - this is the approval workflow from the spec.
    supervisor_approved = models.BooleanField(default=False)
    supervisor_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks_approved",
    )
    supervisor_approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["project"]),
            models.Index(fields=["deadline"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tasks:task_detail", kwargs={"pk": self.pk})

    def clean(self):
        if self.assigned_to_id and self.assigned_to.role != "intern":
            raise ValidationError({"assigned_to": "Tasks can only be assigned to interns."})

    @property
    def is_overdue(self):
        if self.status == self.Status.COMPLETED:
            return False
        return self.deadline < timezone.now()

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.progress_percent = 100
        self.completed_at = timezone.now()


class ProgressUpdate(models.Model):
    """Daily/weekly progress log entries - the audit trail of work done."""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="progress_updates")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    note = models.TextField()
    progress_percent = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    new_status = models.CharField(max_length=20, choices=Task.Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task.title} - {self.progress_percent}% ({self.created_at:%Y-%m-%d})"


class ActivityLog(models.Model):
    """System-wide append-only activity feed, used for history & reporting."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
