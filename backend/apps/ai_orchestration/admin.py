# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import AsyncJob


@admin.register(AsyncJob)
class AsyncJobAdmin(admin.ModelAdmin):
    list_display = [
        "id", "job_type", "status", "team", "project", "owner",
        "progress", "cost", "created_at",
    ]
    list_filter = ["status", "job_type", "team"]
    readonly_fields = ["created_at", "updated_at", "started_at", "completed_at"]
