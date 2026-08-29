# -*- coding: utf-8 -*-
from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default="system")

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_username",
            "action",
            "target_type",
            "target_id",
            "reason",
            "created_at",
        ]
        read_only_fields = fields
