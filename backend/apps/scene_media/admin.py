# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import SceneMedia


@admin.register(SceneMedia)
class SceneMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "scene_id", "media_type", "status", "version", "updated_at")
    list_filter = ("media_type", "status", "team")
    search_fields = ("project__topic", "scene_id")
