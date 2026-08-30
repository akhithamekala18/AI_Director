# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import RegenerationRequest, SceneMediaVersion


@admin.register(RegenerationRequest)
class RegenerationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "scene_id",
        "full",
        "status",
        "media_snapshot_version",
        "created_at",
    )
    list_filter = ("status", "full", "team")
    search_fields = ("project__topic", "scene_id")


@admin.register(SceneMediaVersion)
class SceneMediaVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "media", "scene_id", "media_type", "version", "created_at")
    list_filter = ("media_type",)
