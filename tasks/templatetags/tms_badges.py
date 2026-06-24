"""
Maps our Task.Status values onto the badge-* class names defined in the
theme's CSS, since they don't match 1:1 (e.g. "completed" -> "complete",
"in_progress" -> "inprogress"). Keeping this mapping in one filter avoids
repeating fragile string-slicing logic in every template.
"""
from django import template

register = template.Library()

STATUS_BADGE_MAP = {
    "pending": "badge-pending",
    "in_progress": "badge-inprogress",
    "completed": "badge-complete",
}

PRIORITY_BADGE_MAP = {
    "low": "badge-low",
    "medium": "badge-medium",
    "high": "badge-high",
    "urgent": "badge-urgent",
}


@register.filter
def status_badge_class(status):
    return STATUS_BADGE_MAP.get(status, "badge-new")


@register.filter
def priority_badge_class(priority):
    return PRIORITY_BADGE_MAP.get(priority, "badge-medium")
