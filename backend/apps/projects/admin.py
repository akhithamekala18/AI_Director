from django.contrib import admin

from apps.projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["id", "topic", "lifecycle_state", "team", "is_template", "updated_at"]
    list_filter = ["lifecycle_state", "is_template"]

