# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models


class UserSettings(models.Model):
    """Account and security settings foundation (Day 7, §20.4.2 partial)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settings")
    email_notifications_enabled = models.BooleanField(default=True)
    in_app_notifications_enabled = models.BooleanField(default=True)
    default_voice_style = models.CharField(max_length=64, blank=True, default="")
    default_caption_style = models.CharField(max_length=64, blank=True, default="")
    default_music_mood = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"settings:{self.user_id}"


class StoredCredential(models.Model):
    """Encrypted platform credential (Overview §29.4: encrypted, scoped, never logged).

    The returned API surface never exposes `encrypted_value`; only a masked
    label is shown. Provider publishing scopes are enforced later in B3; the
    foundation proves the encrypted round-trip and revocation.
    """

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credentials")
    provider = models.CharField(max_length=64)
    label = models.CharField(max_length=120)
    encrypted_value = models.TextField()
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("owner", "provider", "label")

    def __str__(self):
        return f"credential:{self.id}:{self.provider}"


class PublishingPreferences(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="publishing_preferences")
    auto_approve_enabled = models.BooleanField(default=False)
    default_posting_time = models.TimeField(null=True, blank=True)
    cross_post_by_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name_plural = "Publishing preferences"
    def __str__(self):
        return f"publishing_prefs:{self.user_id}"


class NotificationPreferences(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    approval_requests = models.BooleanField(default=True)
    reminders = models.BooleanField(default=True)
    publish_outcomes = models.BooleanField(default=True)
    publish_failures = models.BooleanField(default=True)
    team_assignments = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name_plural = "Notification preferences"
    def __str__(self):
        return f"notification_prefs:{self.user_id}"
