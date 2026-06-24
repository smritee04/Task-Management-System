from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, AuditLog, Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "intern_count", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)
    date_hierarchy = "created_at"

    def intern_count(self, obj):
        return obj.interns.count()
    intern_count.short_description = "Interns"


class UserAdmin(BaseUserAdmin):
    list_display = (
        "username", "get_full_name", "email", "role", "domain",
        "supervisor", "is_active", "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff", "domain")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
    date_hierarchy = "date_joined"
    list_per_page = 25
    fieldsets = BaseUserAdmin.fieldsets + (
        ("TMS Role Info", {"fields": ("role", "supervisor", "domain", "phone_number", "profile_photo")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("TMS Role Info", {"fields": ("role", "supervisor", "domain", "phone_number", "email")}),
    )

    def get_full_name(self, obj):
        return obj.get_full_name() or "—"
    get_full_name.short_description = "Name"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "target_user", "detail")
    list_filter = ("action",)
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    search_fields = ("actor__username", "target_user__username", "action", "detail")
    date_hierarchy = "timestamp"
    list_per_page = 25

    def has_add_permission(self, request):
        # Audit logs are system-generated only - never manually creatable.
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(User, UserAdmin)
