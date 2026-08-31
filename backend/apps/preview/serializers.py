# -*- coding: utf-8 -*-
"""Preview serializers (Task 37)."""
from rest_framework import serializers

from .models import PreviewAsset


class PreviewAssetSerializer(serializers.ModelSerializer):
    """Read serializer for PreviewAsset."""

    approved_by = serializers.CharField(source="approved_by.username", default=None)

    class Meta:
        model = PreviewAsset
        fields = [
            "id",
            "project",
            "video",
            "platform_target",
            "aspect_ratio",
            "resolution_width",
            "resolution_height",
            "status",
            "asset_ref",
            "provider",
            "duration_seconds",
            "scene_count",
            "version",
            "approval_state",
            "approved_by",
            "approved_at",
            "rejection_reason",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PreviewGenerateSerializer(serializers.Serializer):
    """Input serializer for generating a preview."""
    platform_target = serializers.CharField(max_length=64, required=False, default="YouTube")


class PreviewApproveSerializer(serializers.Serializer):
    """Input serializer for approving a preview."""
    pass


class PreviewRejectSerializer(serializers.Serializer):
    """Input serializer for rejecting a preview."""
    reason = serializers.CharField(max_length=1024, required=True)
