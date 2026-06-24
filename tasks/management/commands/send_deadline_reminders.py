"""
Sends an in-app notification to interns whose task deadline is within the
next 24 hours and who haven't completed the task yet.

Intended to run on a schedule, e.g. via cron:
    0 * * * * cd /path/to/project && python manage.py send_deadline_reminders

Idempotent: it only notifies once per task by checking whether a reminder
notification already exists for that task in the relevant window.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification
from notifications.services import notify
from tasks.models import Task


class Command(BaseCommand):
    help = "Notify interns of tasks with deadlines in the next 24 hours."

    def handle(self, *args, **options):
        now = timezone.now()
        window_end = now + timedelta(hours=24)

        upcoming = Task.objects.exclude(status=Task.Status.COMPLETED).filter(
            deadline__gte=now, deadline__lte=window_end
        )

        sent = 0
        for task in upcoming:
            already_sent = Notification.objects.filter(
                recipient=task.assigned_to,
                link=task.get_absolute_url(),
                message__startswith="Deadline reminder:",
                created_at__gte=now - timedelta(hours=24),
            ).exists()
            if already_sent:
                continue
            notify(
                recipient=task.assigned_to,
                message=f"Deadline reminder: '{task.title}' is due {task.deadline:%Y-%m-%d %H:%M}.",
                link=task.get_absolute_url(),
            )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} deadline reminder(s)."))
