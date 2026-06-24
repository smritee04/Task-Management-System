"""
Single entry point for creating notifications, so every part of the app
(tasks, feedback, reminders) creates them the same validated way.
"""
from .models import Notification


def notify(recipient, message, link=""):
    if recipient is None:
        return None
    return Notification.objects.create(recipient=recipient, message=message, link=link)
