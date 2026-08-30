# -*- coding: utf-8 -*-
"""DRF serializers for AI orchestration models."""
from rest_framework import serializers

from .models import AsyncJob


class AsyncJobSerializer(serializers.ModelSerializer):
    """Serializer for AsyncJob model."""

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    project_topic = serializers.CharField(source="project.topic", read_only=True)

    class Meta:
        model = AsyncJob
        fields = [
            "id",
            "team",
            "team_name",
            "project",
            "project_topic",
            "owner",
            "owner_username",
            "job_type",
            "status",
            "progress",
            "result",
            "error_message",
            "retry_count",
            "max_retries",
            "cost",
            "cost_currency",
            "provider",
            "metadata",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "team",
            "project",
            "owner",
            "status",
            "progress",
            "result",
            "error_message",
            "retry_count",
            "cost",
            "cost_currency",
            "provider",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        ]


class CreateJobSerializer(serializers.Serializer):
    """Serializer for creating a new job."""

    project_id = serializers.IntegerField()
    job_type = serializers.ChoiceField(choices=AsyncJob.JobType.choices)
    metadata = serializers.JSONField(required=False, default=dict)
