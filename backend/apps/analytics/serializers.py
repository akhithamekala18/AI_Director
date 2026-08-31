# -*- coding: utf-8 -*-
from rest_framework import serializers

from apps.analytics.models import AuditExport, PublishedPerformance


class PublishedPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishedPerformance
        fields = [
            "id", "entry", "platform", "topic",
            "views", "likes", "comments", "shares",
            "engagement_rate", "recorded_at", "updated_at",
        ]
        read_only_fields = ["id", "recorded_at", "updated_at"]


class AuditExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditExport
        fields = ["id", "format", "record_count", "created_at"]
        read_only_fields = fields
