from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["id", "actor", "action", "target_type", "created_at"]
    list_filter = ["action"]
    readonly_fields = ["actor", "action", "target_type", "target_id", "reason", "created_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

