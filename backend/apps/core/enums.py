# -*- coding: utf-8 -*-
"""Domain enums central to the Phase-1 foundation.

Project lifecycle states are authoritative from Project Overview §20.1.1:
Draft -> Researching -> Research Approved -> Scripting -> Script Approved ->
Producing -> Video Approved -> Scheduled -> Published / Archived.
Roles are from Development Plan Day 3 contract and Overview §29.3.
"""

from enum import Enum


class ProjectLifecycle(str, Enum):
    DRAFT = "Draft"
    RESEARCHING = "Researching"
    RESEARCH_APPROVED = "Research Approved"
    SCRIPTING = "Scripting"
    SCRIPT_APPROVED = "Script Approved"
    PRODUCING = "Producing"
    VIDEO_APPROVED = "Video Approved"
    SCHEDULED = "Scheduled"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"


class Role(str, Enum):
    CREATOR = "Creator"
    EDITOR = "Editor"
    REVIEWER = "Reviewer"
    APPROVER_OWNER = "Approver/Owner"
    ADMIN = "Admin"
    VIEWER = "Viewer"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ARCHIVE = "archive"
    RESTORE = "restore"
    DUPLICATE = "duplicate"
    TEMPLATE_FROM = "template_from"
    LIFECYCLE_TRANSITION = "lifecycle_transition"
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_REGISTER = "auth_register"
    CREDENTIAL_SET = "credential_set"
    CREDENTIAL_REVOKED = "credential_revoked"
    SETTINGS_UPDATE = "settings_update"


class NotificationType(str, Enum):
    STATUS = "status"
    APPROVAL_REQUEST = "approval_request"
