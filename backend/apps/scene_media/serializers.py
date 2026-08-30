# -*- coding: utf-8 -*-
"""DRF serializers for scene media (Phase 2F, Task 25)."""
from rest_framework import serializers

from .models import SceneMedia


class SceneMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SceneMedia
        fields = [
            "id",
            "project",
            "team",
            "scene_builder",
            "scene_id",
            "scene_order",
            "media_type",
            "status",
            "asset_ref",
            "provider",
            "provider_metadata",
            "direction",
            "narration",
            "characters",
            "duration_seconds",
            "pacing",
            "transition",
            "voice",
            "music",
            "caption",
            "error_message",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SceneMediaGenerateSerializer(serializers.Serializer):
    """Accepts an optional list of media types to generate."""

    media_types = serializers.ListField(
        child=serializers.ChoiceField(choices=SceneMedia.MediaType.choices),
        required=False,
        allow_empty=False,
    )
