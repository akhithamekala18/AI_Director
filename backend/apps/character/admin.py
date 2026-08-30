# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Character, CharacterLibrary


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "gate_state", "version", "updated_at")
    list_filter = ("gate_state",)
    search_fields = ("project__topic",)


@admin.register(CharacterLibrary)
class CharacterLibraryAdmin(admin.ModelAdmin):
    list_display = ("id", "character_id", "name", "version", "team", "updated_at")
    list_filter = ("team",)
    search_fields = ("character_id", "name")
