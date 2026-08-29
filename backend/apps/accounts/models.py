# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.enums import Role


class Team(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="teams"
    )

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Scopes a user to a team with a single role (Overview §29.2/§29.3)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=24, choices=[(r.value, r.value) for r in Role], default=Role.CREATOR.value)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "team")


class User(AbstractUser):
    """Application user. Passwords are stored only through Django's hasher —
    never in plaintext (Overview §29.4). Team membership scopes access."""

    mfa_enabled = models.BooleanField(default=False)
    # MFA/SSO are surfaced as options only in V1 (decision log DG-6); no
    # provider adapters are wired in the foundation.

    def get_primary_role(self):
        membership = self.memberships.order_by("id").first()
        return membership.role if membership else Role.VIEWER.value

    def __str__(self):
        return self.username
