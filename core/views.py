from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def home_redirect(request):
    """
    Root URL: send authenticated users to their role-appropriate dashboard,
    and anonymous users to the login page. No public landing page leaks
    any data, by design.
    """
    if request.user.is_authenticated:
        return redirect("accounts:post_login_redirect")
    return redirect("accounts:login")
