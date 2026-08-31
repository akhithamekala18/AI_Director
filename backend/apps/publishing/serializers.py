# -*- coding: utf-8 -*-
from rest_framework import serializers
from .models import Approval, PublishingAuditLog, ScheduledEntry, ScheduledPost, SocialAccount, UploadAttempt

class SocialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialAccount
        fields = ["id", "platform", "platform_account_id", "display_name", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

class SocialAccountConnectSerializer(serializers.Serializer):
    platform = serializers.CharField(max_length=64)
    platform_account_id = serializers.CharField(max_length=256)
    display_name = serializers.CharField(max_length=256, required=False, default="")

class ScheduledPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledPost
        fields = ["id", "project", "status", "payload_snapshot", "created_at", "updated_at"]
        read_only_fields = fields

class ScheduledEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledEntry
        fields = ["id", "post", "social_account", "platform", "status", "scheduled_utc", "timezone", "payload_snapshot", "provider_request_id", "created_at", "updated_at"]
        read_only_fields = fields

class EntryCreateSerializer(serializers.Serializer):
    social_account_id = serializers.IntegerField()
    scheduled_utc = serializers.CharField(max_length=64)
    timezone = serializers.CharField(max_length=64, required=False, default="UTC")

class ApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Approval
        fields = ["id", "entry", "actor", "decision", "reason", "granted_at", "expires_at", "invalidated", "invalidated_at"]
        read_only_fields = fields

class ApproveEntrySerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1024, required=False, default="")

class RejectEntrySerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1024, required=False, default="")

class UploadAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadAttempt
        fields = ["id", "entry", "attempt_no", "status", "failure_kind", "provider_request_id", "error_message", "started_at", "finished_at", "created_at"]
        read_only_fields = fields

class PublishingAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishingAuditLog
        fields = ["id", "actor", "action", "entry", "approval", "attempt", "reason", "timestamp"]
        read_only_fields = fields

class PostCreateSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    video_id = serializers.IntegerField(required=False, default=None)
