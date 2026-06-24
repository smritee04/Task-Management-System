import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView

from accounts.models import User
from core.mixins import SupervisorRequiredMixin
from notifications.services import notify
from tasks.models import Task
from .forms import FeedbackItemForm, PerformanceEvaluationForm
from .models import FeedbackItem, PerformanceEvaluation

audit_logger = logging.getLogger("tms.audit")


def _can_comment_on(user, task):
    if user.is_superuser or user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.SUPERVISOR:
        return task.assigned_to.supervisor_id == user.id
    return False


@login_required
def add_feedback(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk)
    if not _can_comment_on(request.user, task):
        raise PermissionDenied("You cannot leave feedback on this task.")

    if request.method != "POST":
        return redirect("tasks:task_detail", pk=task_pk)

    form = FeedbackItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.task = task
        item.author = request.user
        item.save()
        notify(
            recipient=task.assigned_to,
            message=f"New feedback on '{task.title}' from {request.user.get_full_name() or request.user.username}.",
            link=task.get_absolute_url(),
        )
        audit_logger.info("FEEDBACK_ADDED actor=%s task_id=%s", request.user.username, task.pk)
        messages.success(request, "Feedback submitted.")
    else:
        messages.error(request, "Please correct the errors below.")
    return redirect("tasks:task_detail", pk=task_pk)


class EvaluationListView(SupervisorRequiredMixin, ListView):
    """Admins see all evaluations; supervisors see only ones they wrote or
    that concern their own interns."""
    model = PerformanceEvaluation
    template_name = "feedback/evaluation_list.html"
    context_object_name = "evaluations"
    paginate_by = 20

    def get_queryset(self):
        qs = PerformanceEvaluation.objects.select_related("intern", "evaluator")
        user = self.request.user
        if user.is_superuser or user.role == User.Role.ADMIN:
            return qs.order_by("-period_end")
        return qs.filter(intern__supervisor=user).order_by("-period_end")


class EvaluationCreateView(SupervisorRequiredMixin, CreateView):
    model = PerformanceEvaluation
    form_class = PerformanceEvaluationForm
    template_name = "feedback/evaluation_form.html"

    def get_success_url(self):
        from django.urls import reverse
        return reverse("feedback:evaluation_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user = self.request.user
        if user.is_superuser or user.role == User.Role.ADMIN:
            kwargs["assignable_interns"] = User.objects.filter(role=User.Role.INTERN)
        else:
            kwargs["assignable_interns"] = User.objects.filter(role=User.Role.INTERN, supervisor=user)
        return kwargs

    def form_valid(self, form):
        form.instance.evaluator = self.request.user
        response = super().form_valid(form)
        notify(
            recipient=self.object.intern,
            message=f"A new performance evaluation has been recorded for you ({self.object.period_start} to {self.object.period_end}).",
            link="",
        )
        audit_logger.info(
            "EVALUATION_CREATED actor=%s intern=%s score=%s",
            self.request.user.username, self.object.intern.username, self.object.score,
        )
        messages.success(self.request, "Evaluation saved.")
        return response


@login_required
def my_evaluations(request):
    """Interns view their own evaluations only."""
    if not (request.user.is_superuser or request.user.role == User.Role.INTERN):
        raise PermissionDenied
    evaluations = PerformanceEvaluation.objects.filter(intern=request.user).select_related("evaluator")
    return render(request, "feedback/my_evaluations.html", {"evaluations": evaluations})
