# -*- coding: utf-8 -*-
from rest_framework import serializers

from apps.settings_app.models import StoredCredential, UserSettings


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = [
            "id",
            "email_notifications_enabled",
            "in_app_notifications_enabled",
            "default_voice_style",
            "default_caption_style",
            "default_music_mood",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StoredCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredCredential
        fields = ["id", "provider", "label", "revoked", "created_at"]
        read_only_fields = ["id", "created_at"]
