"""
Signal handlers that produce a tamper-evident audit trail of login
activity, independent of whatever view code triggered it.
"""
import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

audit_logger = logging.getLogger("tms.audit")


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    audit_logger.info("LOGIN_SUCCESS user=%s ip=%s", user.username, _client_ip(request))


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user:
        audit_logger.info("LOGOUT user=%s ip=%s", user.username, _client_ip(request))


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request=None, **kwargs):
    username = credentials.get("username", "<unknown>")
    audit_logger.warning(
        "LOGIN_FAILED username=%s ip=%s", username, _client_ip(request) if request else "?"
    )


def _client_ip(request):
    if request is None:
        return "?"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "?")
