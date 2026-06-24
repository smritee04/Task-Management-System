"""
Reporting & analytics views.

Read-only by nature, but still role-scoped: admins see org-wide data,
supervisors see only their own interns' data. Nobody gets a report
containing data they couldn't otherwise see in the rest of the app.
"""
import csv
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import User
from feedback.models import PerformanceEvaluation
from tasks.models import Task

audit_logger = logging.getLogger("tms.audit")


def _scope_tasks(user):
    if user.is_superuser or user.role == User.Role.ADMIN:
        return Task.objects.all()
    if user.role == User.Role.SUPERVISOR:
        return Task.objects.filter(assigned_to__supervisor=user)
    return Task.objects.filter(assigned_to=user)


@login_required
def overview_report(request):
    if request.user.role == User.Role.INTERN and not request.user.is_superuser:
        raise PermissionDenied("Interns do not have access to team reports.")

    tasks = _scope_tasks(request.user)
    by_status = tasks.values("status").annotate(count=Count("id")).order_by("status")
    by_priority = tasks.values("priority").annotate(count=Count("id")).order_by("priority")

    overdue_count = sum(1 for t in tasks.exclude(status=Task.Status.COMPLETED) if t.is_overdue)

    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        interns = User.objects.filter(role=User.Role.INTERN)
    else:
        interns = User.objects.filter(role=User.Role.INTERN, supervisor=request.user)

    per_intern = []
    for intern in interns:
        intern_tasks = tasks.filter(assigned_to=intern)
        total = intern_tasks.count()
        completed = intern_tasks.filter(status=Task.Status.COMPLETED).count()
        per_intern.append({
            "intern": intern,
            "total": total,
            "completed": completed,
            "completion_rate": round((completed / total) * 100, 1) if total else 0,
            "avg_progress": intern_tasks.aggregate(avg=Avg("progress_percent"))["avg"] or 0,
        })

    context = {
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue_count": overdue_count,
        "total_tasks": tasks.count(),
        "per_intern": per_intern,
        "generated_at": timezone.now(),
    }
    return render(request, "reports/overview.html", context)


@login_required
def performance_report(request):
    if request.user.role == User.Role.INTERN and not request.user.is_superuser:
        raise PermissionDenied("Interns do not have access to team reports.")

    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        evaluations = PerformanceEvaluation.objects.select_related("intern", "evaluator")
    else:
        evaluations = PerformanceEvaluation.objects.filter(
            intern__supervisor=request.user
        ).select_related("intern", "evaluator")

    avg_score = evaluations.aggregate(avg=Avg("score"))["avg"] or 0
    return render(request, "reports/performance.html", {
        "evaluations": evaluations.order_by("-period_end"),
        "avg_score": round(avg_score, 1),
    })


@login_required
def export_tasks_csv(request):
    """
    CSV export of the same role-scoped task queryset used elsewhere -
    no separate, looser query path for 'export' that could leak more
    data than the on-screen view shows.
    """
    if request.user.role == User.Role.INTERN and not request.user.is_superuser:
        raise PermissionDenied("Interns do not have access to exports.")

    tasks = _scope_tasks(request.user).select_related("assigned_to", "created_by").order_by("-created_at")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tasks_export.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Title", "Assigned To", "Created By", "Priority", "Status",
        "Progress %", "Deadline", "Supervisor Approved", "Created At",
    ])
    for t in tasks:
        writer.writerow([
            t.title,
            t.assigned_to.username if t.assigned_to else "",
            t.created_by.username if t.created_by else "",
            t.get_priority_display(),
            t.get_status_display(),
            t.progress_percent,
            t.deadline.strftime("%Y-%m-%d %H:%M"),
            "Yes" if t.supervisor_approved else "No",
            t.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    audit_logger.info("REPORT_EXPORTED actor=%s type=tasks_csv", request.user.username)
    return response
