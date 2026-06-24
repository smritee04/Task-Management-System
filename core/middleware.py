"""
Core middleware.

ActiveAccountMiddleware:
    Forces an immediate logout if a logged-in user's account has been
    deactivated (is_active=False) by an admin while their session is still
    alive. Without this, a disabled account could keep using an existing
    session cookie until it expires - a real loophole. This middleware closes
    that gap on every request.
"""
import logging

from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect

audit_logger = logging.getLogger("tms.audit")


class ActiveAccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_active:
            audit_logger.warning(
                "Blocked request from deactivated account: %s", user.username
            )
            logout(request)
            messages.error(
                request, "Your account has been deactivated. Contact an administrator."
            )
            return redirect("accounts:login")

        response = self.get_response(request)
        return response
