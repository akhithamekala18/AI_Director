# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import SceneBuilder


@admin.register(SceneBuilder)
class SceneBuilderAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "gate_state", "version", "updated_at")
    list_filter = ("gate_state",)
    search_fields = ("project__topic",)
