from django import forms

from .models import FeedbackItem, PerformanceEvaluation


class StyledFormMixin:
    def _style_fields(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " form-control").strip()


class FeedbackItemForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FeedbackItem
        fields = ["comment", "rating"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()


class PerformanceEvaluationForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PerformanceEvaluation
        fields = ["intern", "period_start", "period_end", "score", "strengths", "areas_for_improvement", "summary"]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "strengths": forms.Textarea(attrs={"rows": 3}),
            "areas_for_improvement": forms.Textarea(attrs={"rows": 3}),
            "summary": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, assignable_interns=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
        if assignable_interns is not None:
            self.fields["intern"].queryset = assignable_interns

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and start > end:
            self.add_error("period_end", "Period end must be after period start.")
        score = cleaned.get("score")
        if score is not None and not (0 <= score <= 100):
            self.add_error("score", "Score must be between 0 and 100.")
        return cleaned
