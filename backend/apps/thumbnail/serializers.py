# -*- coding: utf-8 -*-
"""DRF serializers for Thumbnail generation (Task 36)."""
from rest_framework import serializers

from .models import ThumbnailAsset


class ThumbnailAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThumbnailAsset
        fields = [
            "id",
            "project",
            "team",
            "scene_builder",
            "platform_target",
            "width",
            "height",
            "status",
            "asset_ref",
            "provider",
            "provider_metadata",
            "title_text",
            "variations",
            "version",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ThumbnailGenerateSerializer(serializers.Serializer):
    """Accepts optional platform target and title text."""
    platform_target = serializers.CharField(required=False, allow_blank=True, default="")
    title_text = serializers.CharField(required=False, allow_blank=True, default="")
