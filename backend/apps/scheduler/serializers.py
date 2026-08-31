# -*- coding: utf-8 -*-
"""Scheduler serializers (Task 38)."""
from rest_framework import serializers

from .models import ScheduleEntry


class ScheduleEntrySerializer(serializers.ModelSerializer):
    """Read serializer for ScheduleEntry."""

    class Meta:
        model = ScheduleEntry
        fields = [
            "id",
            "project",
            "platform",
            "scheduled_local_datetime",
            "timezone",
            "scheduled_utc_datetime",
            "status",
            "best_time_suggestion",
            "reminder_sent",
            "reminder_scheduled_at",
            "cancelled_at",
            "cancellation_reason",
            "published_at",
            "version",
            "previous_scheduled_utc",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ScheduleCreateSerializer(serializers.Serializer):
    """Input serializer for creating a schedule entry."""
    platform = serializers.CharField(max_length=64)
    scheduled_local_datetime = serializers.CharField(max_length=64)
    timezone = serializers.CharField(max_length=64, required=False, default="UTC")


class ScheduleRescheduleSerializer(serializers.Serializer):
    """Input serializer for rescheduling."""
    scheduled_local_datetime = serializers.CharField(max_length=64)
    timezone = serializers.CharField(max_length=64, required=False, default=None)


class ScheduleCancelSerializer(serializers.Serializer):
    """Input serializer for cancelling."""
    reason = serializers.CharField(max_length=1024, required=False, default="")
