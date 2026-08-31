# -*- coding: utf-8 -*-
"""DRF serializers for Video generation (Task 36)."""
from rest_framework import serializers

from .models import VideoAsset


class VideoAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = [
            "id",
            "project",
            "team",
            "scene_builder",
            "platform_target",
            "aspect_ratio",
            "resolution_width",
            "resolution_height",
            "status",
            "asset_ref",
            "provider",
            "provider_metadata",
            "duration_seconds",
            "scene_count",
            "version",
            "error_message",
            "retry_count",
            "max_retries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class VideoGenerateSerializer(serializers.Serializer):
    """Accepts optional platform target for video generation."""
    platform_target = serializers.CharField(required=False, allow_blank=True, default="")
