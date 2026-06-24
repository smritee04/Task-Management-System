from django.contrib import admin

from .models import FeedbackItem, PerformanceEvaluation


@admin.register(FeedbackItem)
class FeedbackItemAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "rating", "comment", "created_at")
    list_filter = ("rating",)
    search_fields = ("task__title", "author__username", "comment")
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(PerformanceEvaluation)
class PerformanceEvaluationAdmin(admin.ModelAdmin):
    list_display = ("intern", "evaluator", "period_start", "period_end", "score")
    list_filter = ("evaluator",)
    search_fields = ("intern__username", "evaluator__username")
    date_hierarchy = "period_start"
    list_per_page = 25
