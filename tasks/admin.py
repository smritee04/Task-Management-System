from django.contrib import admin

from .models import Task, ProgressUpdate, ActivityLog, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_by", "start_date", "deadline", "task_count", "completed_task_count")
    list_filter = ("status",)
    search_fields = ("name", "description")
    autocomplete_fields = ["created_by"]
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title", "project", "assigned_to", "priority", "status",
        "progress_percent", "deadline", "supervisor_approved",
    )
    list_filter = ("status", "priority", "supervisor_approved", "project")
    search_fields = ("title", "description", "assigned_to__username", "project__name")
    autocomplete_fields = ["assigned_to", "created_by", "supervisor_approved_by", "project"]
    date_hierarchy = "deadline"
    list_per_page = 25


@admin.register(ProgressUpdate)
class ProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ("task", "submitted_by", "progress_percent", "new_status", "created_at")
    list_filter = ("new_status",)
    search_fields = ("task__title", "submitted_by__username", "note")
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "task", "message")
    list_filter = ("user",)
    search_fields = ("message", "user__username", "task__title")
    date_hierarchy = "created_at"
    list_per_page = 25

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
