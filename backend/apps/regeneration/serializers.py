# -*- coding: utf-8 -*-
"""DRF serializers for regeneration (Phase 2G, Task 26)."""
from rest_framework import serializers

from apps.scene_media.models import SceneMedia

from .models import RegenerationRequest, SceneMediaVersion


class SceneMediaVersionSerializer(serializers.ModelSerializer):
    """Immutable previous-version snapshot (for compare)."""

    class Meta:
        model = SceneMediaVersion
        fields = [
            "id",
            "media",
            "regeneration",
            "version",
            "media_type",
            "scene_id",
            "scene_order",
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
            "created_at",
        ]
        read_only_fields = fields


class RegenerationRequestSerializer(serializers.ModelSerializer):
    """Read projection of a regeneration request."""

    snapshots = SceneMediaVersionSerializer(many=True, read_only=True)

    class Meta:
        model = RegenerationRequest
        fields = [
            "id",
            "project",
            "team",
            "scene_builder",
            "created_by",
            "scene_id",
            "media_types",
            "full",
            "status",
            "async_job",
            "media_snapshot_version",
            "error_message",
            "snapshots",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RegenerationRequestCreateSerializer(serializers.Serializer):
    """Accepts the regeneration scope.

    G-4: scoped single scene by default (scene_id required); full regeneration
    only when ``full`` is explicitly true.
    """

    scene_id = serializers.CharField(
        required=False, allow_blank=True, max_length=64
    )
    media_types = serializers.ListField(
        child=serializers.ChoiceField(choices=SceneMedia.MediaType.choices),
        required=False,
        allow_empty=True,
    )
    full = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        full = attrs.get("full", False)
        scene_id = attrs.get("scene_id")
        if not full and not scene_id:
            raise serializers.ValidationError(
                "scene_id is required unless full regeneration is requested"
            )
        return attrs
