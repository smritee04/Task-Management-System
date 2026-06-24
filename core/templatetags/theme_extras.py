"""
Small template filters used purely for theme presentation
(e.g. turning the 'in_progress' status value into 'inprogress' so it
matches the .badge-inprogress CSS class from the theme).
"""
from django import template

register = template.Library()


@register.filter
def nounderscore(value):
    """Remove underscores - used to map model status values to CSS class
    suffixes (in_progress -> inprogress)."""
    return str(value).replace("_", "")


@register.filter
def initials(user):
    """Return up to 2 uppercase initials for an avatar circle."""
    if not user:
        return "?"
    first = (getattr(user, "first_name", "") or "")[:1]
    last = (getattr(user, "last_name", "") or "")[:1]
    combo = (first + last).upper()
    if combo:
        return combo
    username = getattr(user, "username", "") or "?"
    return username[:2].upper()
