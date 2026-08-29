# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from apps.core.enums import NotificationType


class Notification(models.Model):
    """In-app notification primitive (Development Plan Day 9, §20.3.3).

    Supports status events and approval-request events (which carry an artifact
    link). Delivered in-app only in the foundation; delivery channels (email/push/
    SMS) are a deferred decision (DG-12) and arrive in B3.
    """

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=32, choices=[(t.value, t.value) for t in NotificationType])
    title = models.CharField(max_length=160)
    message = models.CharField(max_length=500, blank=True, default="")
    artifact_type = models.CharField(max_length=64, blank=True, default="")
    artifact_id = models.CharField(max_length=64, blank=True, default="")
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.type}] for {self.recipient_id}: {self.title}"
