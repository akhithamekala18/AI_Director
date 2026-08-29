# -*- coding: utf-8 -*-
"""RBAC capability matrix (Overview §29.3, Development Plan Day 5).

Roles are ordered by privilege. Every server-side permission check consults this
matrix; the UI only mirrors it (strict stream-separation rule, Roadmap §2.2).

Publishing approval is restricted to accountable roles and can never be
triggered by Viewer or Reviewer. In the foundation (B1) publishing has no
endpoint at all; the matrix is the frozen contract the B3 publishing service and
the F3 UI both follow.
"""

from apps.core.enums import Role

from rest_framework.permissions import BasePermission

# Ordered most-privileged to least.
ROLE_ORDER = [
    Role.ADMIN,
    Role.APPROVER_OWNER,
    Role.CREATOR,
    Role.EDITOR,
    Role.REVIEWER,
    Role.VIEWER,
]

# Capabilities and the minimum role that holds them.
CAPABILITIES = {
    # Everything a "manage projects" workspace needs (B1/F1 scope).
    "view_projects": Role.VIEWER,
    "manage_projects": Role.EDITOR,  # create/edit/duplicate/template/archive
    "manage_settings": Role.CREATOR,
    "view_audit": Role.EDITOR,
    # Publishing is approval-gated and restricted to accountable roles (G-3).
    # No publish endpoint exists in B1; these reflect the frozen §29.3 matrix.
    "approve": Role.APPROVER_OWNER,  # Approver/Owner and Admin may approve
    "publish": Role.APPROVER_OWNER,  # only Approver/Owner and Admin may publish
    "admin": Role.ADMIN,
}


def role_rank(role):
    for i, r in enumerate(ROLE_ORDER):
        if r == role:
            return i
    return len(ROLE_ORDER)


def has_capability(role, capability):
    """Return True if the role holds the capability (strictly by matrix)."""
    required = CAPABILITIES.get(capability)
    if required is None:
        return False
    return role_rank(role) <= role_rank(required)


def role_can_manage_projects(role):
    return has_capability(role, "manage_projects")


class HasCapability(BasePermission):
    """DRF permission enforcing a single capability by the user's primary role."""

    capability = None  # subclasses set this, or pass via view.capability

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        capability = getattr(view, "capability", None) or self.capability
        if not capability:
            return True
        role = request.user.get_primary_role()
        if role not in [r.value for r in Role]:
            role = Role.VIEWER.value
        return has_capability(Role(role), capability)
