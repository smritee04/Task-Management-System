from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        # Always scoped to the current user - nobody can list anyone
        # else's notifications, regardless of role.
        return Notification.objects.filter(recipient=self.request.user)


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk)
    if notification.recipient_id != request.user.id:
        raise PermissionDenied
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    next_url = notification.link or "notifications:notification_list"
    return redirect(next_url)


@login_required
def mark_all_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:notification_list")
