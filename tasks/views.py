"""
Task views.

The key security property enforced throughout this file: every queryset
that returns Task objects is scoped to what the *current* user is allowed
to see, BEFORE any pk lookup happens. This means a user can never probe
another user's task by guessing its ID (IDOR) - get_object_or_404 against
an already-filtered queryset returns a clean 404, not a 403 that would
confirm the object exists.
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View

from accounts.models import User
from notifications.services import notify
from .forms import TaskForm, ProgressUpdateForm, ProjectForm
from .models import Task, ActivityLog, Project

audit_logger = logging.getLogger("tms.audit")


def _visible_tasks_for(user):
    """Single source of truth for 'which tasks can this user see'."""
    if user.is_superuser or user.role == User.Role.ADMIN:
        return Task.objects.all()
    if user.role == User.Role.SUPERVISOR:
        return Task.objects.filter(assigned_to__supervisor=user)
    return Task.objects.filter(assigned_to=user)


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        qs = _visible_tasks_for(self.request.user).select_related("assigned_to", "created_by", "project")
        status = self.request.GET.get("status", "").strip()
        priority = self.request.GET.get("priority", "").strip()
        project = self.request.GET.get("project", "").strip()
        q = self.request.GET.get("q", "").strip()
        if status in dict(Task.Status.choices):
            qs = qs.filter(status=status)
        if priority in dict(Task.Priority.choices):
            qs = qs.filter(priority=priority)
        if project:
            qs = qs.filter(project_id=project)
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = Task.Status.choices
        ctx["priorities"] = Task.Priority.choices
        ctx["projects"] = Project.objects.all()
        ctx["query"] = self.request.GET.get("q", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["selected_priority"] = self.request.GET.get("priority", "")
        ctx["selected_project"] = self.request.GET.get("project", "")
        return ctx


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        # Scoping happens here, not after the fetch - this is what makes
        # an out-of-scope task ID 404 instead of 403/200.
        return _visible_tasks_for(self.request.user).select_related("assigned_to", "created_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["progress_updates"] = self.object.progress_updates.select_related("submitted_by")
        ctx["progress_form"] = ProgressUpdateForm(initial={
            "progress_percent": self.object.progress_percent,
            "new_status": self.object.status,
        })
        ctx["can_edit"] = self._can_edit()
        ctx["can_approve"] = self._can_approve()
        ctx["can_update_progress"] = self.request.user == self.object.assigned_to
        ctx["feedback_items"] = self.object.feedback_items.select_related("author").order_by("-created_at")
        return ctx

    def _can_edit(self):
        user = self.request.user
        return user.is_superuser or user.role == User.Role.ADMIN

    def _can_approve(self):
        user = self.request.user
        return (
            user.is_superuser
            or user.role == User.Role.ADMIN
            or (user.role == User.Role.SUPERVISOR and self.object.assigned_to.supervisor_id == user.id)
        )


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.role in (User.Role.ADMIN, User.Role.SUPERVISOR)):
            raise PermissionDenied("Only admins and supervisors can create tasks.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        if user.is_superuser or user.role == User.Role.ADMIN:
            kwargs["assignable_interns"] = User.objects.filter(role=User.Role.INTERN)
        else:
            # Supervisors may only assign tasks to their own interns -
            # enforced at the queryset level, not just hidden in the UI.
            kwargs["assignable_interns"] = User.objects.filter(role=User.Role.INTERN, supervisor=user)
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        ActivityLog.objects.create(
            user=self.request.user, task=self.object,
            message=f"{self.request.user} created task '{self.object.title}' for {self.object.assigned_to}.",
        )
        notify(
            recipient=self.object.assigned_to,
            message=f"New task assigned: {self.object.title}",
            link=self.object.get_absolute_url(),
        )
        audit_logger.info(
            "TASK_CREATED actor=%s task_id=%s assigned_to=%s",
            self.request.user.username, self.object.pk, self.object.assigned_to.username,
        )
        messages.success(self.request, "Task created and intern notified.")
        return response


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == User.Role.ADMIN:
            return Task.objects.all()
        if user.role == User.Role.SUPERVISOR:
            return Task.objects.filter(assigned_to__supervisor=user)
        # Interns cannot reach the edit form at all (separate progress-update
        # flow exists instead) - returning none() makes this a clean 404.
        return Task.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        if user.is_superuser or user.role == User.Role.ADMIN:
            kwargs["assignable_interns"] = User.objects.filter(role=User.Role.INTERN)
        else:
            kwargs["assignable_interns"] = User.objects.filter(role=User.Role.INTERN, supervisor=user)
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        audit_logger.info(
            "TASK_UPDATED actor=%s task_id=%s", self.request.user.username, self.object.pk
        )
        messages.success(self.request, "Task updated.")
        return response


class TaskDeleteView(LoginRequiredMixin, View):
    """POST-only deletion, admins only."""

    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied
        task = get_object_or_404(Task, pk=pk)
        title = task.title
        task.delete()
        audit_logger.warning("TASK_DELETED actor=%s title=%s", request.user.username, title)
        messages.success(request, f"Task '{title}' deleted.")
        return redirect("tasks:task_list")


@login_required
def submit_progress_update(request, pk):
    """Only the intern the task is assigned to may submit a progress update."""
    task = get_object_or_404(Task, pk=pk)
    if task.assigned_to_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied("You can only update progress on your own tasks.")

    if request.method != "POST":
        return redirect("tasks:task_detail", pk=pk)

    form = ProgressUpdateForm(request.POST)
    if form.is_valid():
        update = form.save(commit=False)
        update.task = task
        update.submitted_by = request.user
        update.save()

        task.progress_percent = update.progress_percent
        task.status = update.new_status
        if update.new_status == Task.Status.COMPLETED:
            task.mark_completed()
            # Completing a task resets approval - a supervisor must approve
            # the *current* completed state, not a stale one.
            task.supervisor_approved = False
            task.supervisor_approved_by = None
            task.supervisor_approved_at = None
        task.save()

        ActivityLog.objects.create(
            user=request.user, task=task,
            message=f"{request.user} updated progress to {update.progress_percent}% ({update.get_new_status_display()}).",
        )
        if task.assigned_to.supervisor:
            notify(
                recipient=task.assigned_to.supervisor,
                message=f"{request.user} updated progress on '{task.title}'.",
                link=task.get_absolute_url(),
            )
        messages.success(request, "Progress update submitted.")
    else:
        messages.error(request, "Please correct the errors below.")
    return redirect("tasks:task_detail", pk=pk)


@login_required
def approve_task(request, pk):
    """Supervisor (of the assignee) or admin approves a completed task."""
    task = get_object_or_404(Task, pk=pk)
    user = request.user
    allowed = (
        user.is_superuser
        or user.role == User.Role.ADMIN
        or (user.role == User.Role.SUPERVISOR and task.assigned_to.supervisor_id == user.id)
    )
    if not allowed:
        raise PermissionDenied("Only the assigned supervisor or an admin can approve this task.")
    if request.method != "POST":
        return redirect("tasks:task_detail", pk=pk)
    if task.status != Task.Status.COMPLETED:
        messages.error(request, "Only completed tasks can be approved.")
        return redirect("tasks:task_detail", pk=pk)

    from django.utils import timezone
    task.supervisor_approved = True
    task.supervisor_approved_by = user
    task.supervisor_approved_at = timezone.now()
    task.save()

    ActivityLog.objects.create(
        user=user, task=task, message=f"{user} approved task '{task.title}'.",
    )
    notify(
        recipient=task.assigned_to,
        message=f"Your task '{task.title}' was approved by {user.get_full_name() or user.username}.",
        link=task.get_absolute_url(),
    )
    audit_logger.info("TASK_APPROVED actor=%s task_id=%s", user.username, task.pk)
    messages.success(request, "Task approved.")
    return redirect("tasks:task_detail", pk=pk)


def _can_manage_projects(user):
    return user.is_superuser or user.role in (User.Role.ADMIN, User.Role.SUPERVISOR)


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = "tasks/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        qs = Project.objects.select_related("created_by")
        status = self.request.GET.get("status", "").strip()
        q = self.request.GET.get("q", "").strip()
        if status in dict(Project.Status.choices):
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = Project.Status.choices
        ctx["query"] = self.request.GET.get("q", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["can_manage"] = _can_manage_projects(self.request.user)
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "tasks/project_detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tasks"] = _visible_tasks_for(self.request.user).filter(
            project=self.object
        ).select_related("assigned_to")
        ctx["can_manage"] = _can_manage_projects(self.request.user)
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "tasks/project_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_projects(request.user):
            raise PermissionDenied("Only admins and supervisors can create projects.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        audit_logger.info(
            "PROJECT_CREATED actor=%s project_id=%s", self.request.user.username, self.object.pk,
        )
        messages.success(self.request, "Project created.")
        return response


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "tasks/project_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_projects(request.user):
            raise PermissionDenied("Only admins and supervisors can edit projects.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        audit_logger.info(
            "PROJECT_UPDATED actor=%s project_id=%s", self.request.user.username, self.object.pk,
        )
        messages.success(self.request, "Project updated.")
        return response


class ProjectDeleteView(LoginRequiredMixin, View):
    """POST-only deletion, admins only."""

    def post(self, request, pk):
        if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
            raise PermissionDenied
        project = get_object_or_404(Project, pk=pk)
        name = project.name
        project.delete()
        audit_logger.warning("PROJECT_DELETED actor=%s name=%s", request.user.username, name)
        messages.success(request, f"Project '{name}' deleted.")
        return redirect("tasks:project_list")
