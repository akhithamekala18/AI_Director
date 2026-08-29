# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from apps.core.enums import ProjectLifecycle


class Project(models.Model):
    """A production container owning all pipeline stages (Overview §20.1.1).

    Lifecycle is enforced by apps.core.state_machine; this model stores the
    current state and exposes forward/archive transitions that validate against
    the state machine before persisting. Belongs to a team, so access is
    team-scoped (Overview §29.2).
    """

    team = models.ForeignKey("accounts.Team", on_delete=models.CASCADE, related_name="projects")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_projects")
    topic = models.CharField(max_length=255)
    platform_target = models.CharField(max_length=64, blank=True, default="")
    format = models.CharField(max_length=64, blank=True, default="")
    lifecycle_state = models.CharField(
        max_length=32,
        choices=[(s.value, s.value) for s in ProjectLifecycle],
        default=ProjectLifecycle.DRAFT.value,
    )
    is_template = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["team"]), models.Index(fields=["lifecycle_state"])]

    def __str__(self):
        return f"{self.topic} ({self.lifecycle_state})"
