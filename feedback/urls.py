from django.urls import path

from . import views

app_name = "feedback"

urlpatterns = [
    path("task/<int:task_pk>/add/", views.add_feedback, name="add_feedback"),
    path("evaluations/", views.EvaluationListView.as_view(), name="evaluation_list"),
    path("evaluations/new/", views.EvaluationCreateView.as_view(), name="evaluation_create"),
    path("evaluations/mine/", views.my_evaluations, name="my_evaluations"),
]
