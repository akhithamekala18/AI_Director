# -*- coding: utf-8 -*-
from rest_framework import serializers

from apps.core.enums import ProjectLifecycle
from apps.projects.models import Project
from apps.projects.services import next_required_action


class ProjectSerializer(serializers.ModelSerializer):
    next_required_action = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "topic",
            "platform_target",
            "format",
            "lifecycle_state",
            "next_required_action",
            "is_template",
            "owner_username",
            "team_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "lifecycle_state"]

    def get_next_required_action(self, obj):
        return next_required_action(obj.lifecycle_state)


class ProjectTransitionSerializer(serializers.Serializer):
    target_state = serializers.ChoiceField(choices=[s.value for s in ProjectLifecycle])
