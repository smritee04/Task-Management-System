"""
Signal handlers for the tasks app.

Deadline reminders are handled by the management command
`send_deadline_reminders` (see tasks/management/commands), intended to be
run on a schedule (cron / Celery beat / etc.), rather than as a signal,
since "X hours before deadline" is time-based, not event-based.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Task

audit_logger = logging.getLogger("tms.audit")


@receiver(post_save, sender=Task)
def log_task_save(sender, instance, created, **kwargs):
    if created:
        audit_logger.info("TASK_SAVED_NEW id=%s title=%s", instance.pk, instance.title)
