# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Research, ResearchGap, ResearchSource


class ResearchSourceInline(admin.TabularInline):
    model = ResearchSource
    extra = 0


class ResearchGapInline(admin.TabularInline):
    model = ResearchGap
    extra = 0


@admin.register(Research)
class ResearchAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "gate_state", "version", "updated_at")
    list_filter = ("gate_state",)
    search_fields = ("project__topic", "summary")
    inlines = [ResearchSourceInline, ResearchGapInline]


@admin.register(ResearchSource)
class ResearchSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "research", "title", "credibility_score", "url")


@admin.register(ResearchGap)
class ResearchGapAdmin(admin.ModelAdmin):
    list_display = ("id", "research", "gap_type", "status", "description")
    list_filter = ("gap_type", "status")
