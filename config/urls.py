"""Root URL configuration for the TMS project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views import home_redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_redirect, name="home"),
    path("accounts/", include("accounts.urls")),
    path("tasks/", include("tasks.urls")),
    path("feedback/", include("feedback.urls")),
    path("notifications/", include("notifications.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
