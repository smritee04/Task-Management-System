def unread_notifications(request):
    """
    Makes the unread notification count and latest items available in
    every template (for the navbar bell icon) without each view having
    to remember to pass them in.
    """
    if not request.user.is_authenticated:
        return {}
    qs = request.user.notifications.filter(is_read=False)
    return {
        "unread_notification_count": qs.count(),
        "latest_notifications": request.user.notifications.all()[:5],
    }
