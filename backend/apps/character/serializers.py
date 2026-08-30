# -*- coding: utf-8 -*-
"""DRF serializers for the Character Library (Phase 2D, Task 23)."""
from rest_framework import serializers

from .models import Character, CharacterLibrary


class CharacterSerializer(serializers.ModelSerializer):
    approval_actor_username = serializers.CharField(
        source="approval_actor.username", read_only=True, default=None
    )
    character_count = serializers.SerializerMethodField()
    script = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Character
        fields = [
            "id",
            "project",
            "team",
            "script",
            "characters",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "character_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "team",
            "script",
            "characters",
            "gate_state",
            "version",
            "rejection_reason",
            "approval_actor_username",
            "approval_at",
            "character_count",
            "created_at",
            "updated_at",
        ]

    def get_character_count(self, obj):
        return len(obj.characters or [])


class CharacterLibrarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterLibrary
        fields = [
            "id",
            "character_id",
            "name",
            "age",
            "gender",
            "appearance",
            "clothing",
            "accessories",
            "style",
            "version",
            "origin_project",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
