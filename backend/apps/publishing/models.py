# -*- coding: utf-8 -*-
from django.db import models

class SocialAccount(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="social_accounts")
    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE, related_name="social_accounts")
    platform = models.CharField(max_length=64)
    platform_account_id = models.CharField(max_length=256)
    display_name = models.CharField(max_length=256, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    encrypted_tokens = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["platform", "display_name"]
        constraints = [models.UniqueConstraint(fields=["owner", "platform", "platform_account_id"], name="uniq_social_account_owner_platform_id")]
    def __str__(self):
        return f"{self.platform}: {self.display_name or self.platform_account_id}"

class ScheduledPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHING = "publishing", "Publishing"
        PUBLISHED = "published", "Published"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="scheduled_posts")
    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE, related_name="scheduled_posts")
    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="scheduled_posts")
    video = models.ForeignKey("video.VideoAsset", on_delete=models.CASCADE, related_name="scheduled_posts", null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    payload_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-created_at"]
    def __str__(self):
        return f"Post #{self.id} ({self.project_id}) - {self.status}"

class ScheduledEntry(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        READY_FOR_APPROVAL = "ready_for_approval", "Ready for Approval"
        APPROVED = "approved", "Approved"
        APPROVAL_INVALIDATED = "approval_invalidated", "Approval Invalidated"
        REJECTED = "rejected", "Rejected"
        UPLOADING = "uploading", "Uploading"
        PUBLISHED = "published", "Published"
        UPLOAD_FAILED = "upload_failed", "Upload Failed"
        FAILED = "failed", "Failed"
        FAILED_PENDING_USER = "failed_pending_user", "Failed (Pending User)"
        CANCELED = "canceled", "Canceled"
        DELETED = "deleted", "Deleted"
    post = models.ForeignKey(ScheduledPost, on_delete=models.CASCADE, related_name="entries")
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name="entries")
    platform = models.CharField(max_length=64)
    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE, related_name="scheduled_entries")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    scheduled_utc = models.DateTimeField()
    timezone = models.CharField(max_length=64, default="UTC")
    payload_snapshot = models.JSONField(default=dict, blank=True)
    provider_request_id = models.CharField(max_length=256, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["scheduled_utc"]
        constraints = [models.UniqueConstraint(fields=["post", "platform"], name="uniq_entry_post_platform")]
    def __str__(self):
        return f"Entry #{self.id} ({self.platform}) - {self.status}"

class Approval(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
    entry = models.ForeignKey(ScheduledEntry, on_delete=models.CASCADE, related_name="approvals")
    actor = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="publishing_approvals")
    decision = models.CharField(max_length=16, choices=Decision.choices)
    reason = models.TextField(blank=True, default="")
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    invalidated = models.BooleanField(default=False)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ["-granted_at"]
    def __str__(self):
        return f"Approval #{self.id} ({self.decision}) for entry {self.entry_id}"
    @property
    def is_valid(self):
        if self.decision != self.Decision.APPROVE:
            return False
        if self.invalidated:
            return False
        if self.expires_at is not None:
            from django.utils import timezone as dj_tz
            return dj_tz.now() <= self.expires_at
        return True

class UploadAttempt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
    class FailureKind(models.TextChoices):
        NONE = "none", "None"
        TRANSIENT = "transient", "Transient"
        PERMANENT = "permanent", "Permanent"
    entry = models.ForeignKey(ScheduledEntry, on_delete=models.CASCADE, related_name="upload_attempts")
    attempt_no = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    failure_kind = models.CharField(max_length=16, choices=FailureKind.choices, default=FailureKind.NONE)
    provider_request_id = models.CharField(max_length=256, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["entry", "attempt_no"]
    def __str__(self):
        return f"Attempt #{self.attempt_no} for entry {self.entry_id} - {self.status}"

class PublishingAuditLog(models.Model):
    actor = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="publishing_audit_logs")
    action = models.CharField(max_length=64)
    entry = models.ForeignKey(ScheduledEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    approval = models.ForeignKey(Approval, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    attempt = models.ForeignKey(UploadAttempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    reason = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Publishing audit logs"
    def __str__(self):
        return f"Audit: {self.action} by {self.actor_id} at {self.timestamp}"
