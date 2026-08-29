# -*- coding: utf-8 -*-
from django.contrib import admin

from apps.accounts.models import Membership, Team, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "is_active", "mfa_enabled"]
    list_filter = ["is_active"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "team", "role"]
