# -*- coding: utf-8 -*-
"""DRF serializers for the script engine (Phase 2C)."""
from rest_framework import serializers

from .models import Script


class ScriptSerializer(serializers.ModelSerializer):
    approval_actor_username = serializers.CharField(
        source="approval_actor.username", read_only=True, default=None
    )
    scene_count = serializers.SerializerMethodField()
    research = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Script
        fields = [
            "id",
            "project",
            "team",
            "research",
            "title",
            "outline",
            "script",
            "narration",
            "scenes",
            "captions",
            "hashtags",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "scene_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "team",
            "research",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "scenes",
            "captions",
            "hashtags",
            "created_at",
            "updated_at",
        ]

    def get_scene_count(self, obj):
        return len(obj.scenes or [])
