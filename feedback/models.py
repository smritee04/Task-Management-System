from django.conf import settings
from django.db import models

from tasks.models import Task


class FeedbackItem(models.Model):
    """A comment/review note left on a task by an admin or supervisor."""

    class Rating(models.IntegerChoices):
        UNRATED = 0, "Not rated"
        NEEDS_IMPROVEMENT = 1, "Needs Improvement"
        SATISFACTORY = 2, "Satisfactory"
        GOOD = 3, "Good"
        EXCELLENT = 4, "Excellent"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="feedback_items")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    comment = models.TextField()
    rating = models.IntegerField(choices=Rating.choices, default=Rating.UNRATED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback on {self.task.title} by {self.author}"


class PerformanceEvaluation(models.Model):
    """
    A periodic, structured evaluation of an intern by their supervisor -
    distinct from per-task comments, this is the bigger-picture review
    used for performance reporting.
    """
    intern = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="evaluations_received", limit_choices_to={"role": "intern"},
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="evaluations_given",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    score = models.PositiveIntegerField(help_text="Overall score out of 100")
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_end"]

    def __str__(self):
        return f"Evaluation of {self.intern} ({self.period_start} - {self.period_end})"
