# -*- coding: utf-8 -*-
from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "message", "artifact_type", "artifact_id", "read", "created_at"]
        read_only_fields = fields
