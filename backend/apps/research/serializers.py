# -*- coding: utf-8 -*-
"""DRF serializers for the research engine (R6)."""
from rest_framework import serializers

from .models import Research, ResearchGap, ResearchSource


class ResearchSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchSource
        fields = [
            "id",
            "url",
            "title",
            "snippet",
            "credibility_score",
            "accessed_at",
            "created_at",
        ]


class ResearchGapSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchGap
        fields = [
            "id",
            "gap_type",
            "description",
            "source_a",
            "source_b",
            "status",
            "created_at",
        ]


class ResearchSerializer(serializers.ModelSerializer):
    approval_actor_username = serializers.CharField(
        source="approval_actor.username", read_only=True, default=None
    )
    source_count = serializers.IntegerField(read_only=True)
    gap_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Research
        fields = [
            "id",
            "project",
            "team",
            "summary",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "source_count",
            "gap_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "team",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "created_at",
            "updated_at",
        ]
