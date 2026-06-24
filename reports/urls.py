from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("overview/", views.overview_report, name="overview"),
    path("performance/", views.performance_report, name="performance"),
    path("export/tasks.csv", views.export_tasks_csv, name="export_tasks_csv"),
]
