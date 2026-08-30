# -*- coding: utf-8 -*-
"""DRF serializers for the Scene Builder (Phase 2E, Task 24)."""
from rest_framework import serializers

from .models import SceneBuilder


class SceneBuilderSerializer(serializers.ModelSerializer):
    approval_actor_username = serializers.CharField(
        source="approval_actor.username", read_only=True, default=None
    )
    scene_count = serializers.SerializerMethodField()
    script = serializers.PrimaryKeyRelatedField(read_only=True)
    character_set = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SceneBuilder
        fields = [
            "id",
            "project",
            "team",
            "script",
            "character_set",
            "scenes",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "scene_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_scene_count(self, obj):
        return len(obj.scenes or [])
