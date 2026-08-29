# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Append-only audit record (Overview §5.8, G-7; Development Plan Day 8).

    Every state-mutating action records actor, time, action, and reason. The
    record is deliberately append-only: save only happens on create and delete
    is disabled, so the trail cannot be silently altered.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=48)
    target_type = models.CharField(max_length=64, blank=True, default="")
    target_id = models.CharField(max_length=64, blank=True, default="")
    reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise models.ProtectedError("AuditLog is append-only and cannot be modified", self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise models.ProtectedError("AuditLog is append-only and cannot be deleted", self)

    def __str__(self):
        return f"#{self.pk} {self.action} by {self.actor_id} at {self.created_at}"
