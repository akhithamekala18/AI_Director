# -*- coding: utf-8 -*-
"""Server-side RBAC enforcement tests (Development Plan Day 5, §29.3 matrix).

Two users share one team with different roles; verify the capability matrix is
enforced by the backend (a Viewer can never manage/approve/publish; an Editor
can manage but not approve/publish; an Approver/Owner can).
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team
from apps.accounts.permissions import has_capability
from apps.core.enums import Role


def _make_user(username, role, team, password="LongPass123!"):
    User = get_user_model()
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password=password)
    user.memberships.create(team=team, role=role)
    return user


def _client_for(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def shared_team(db):
    return Team.objects.create(name="shared workspace")


@pytest.fixture
def rbac_clients(db, shared_team):
    creator = _make_user("rbac_creator", Role.CREATOR.value, shared_team)
    editor = _make_user("rbac_editor", Role.EDITOR.value, shared_team)
    reviewer = _make_user("rbac_reviewer", Role.REVIEWER.value, shared_team)
    approver = _make_user("rbac_approver", Role.APPROVER_OWNER.value, shared_team)
    admin = _make_user("rbac_admin", Role.ADMIN.value, shared_team)
    viewer = _make_user("rbac_viewer", Role.VIEWER.value, shared_team)
    return {
        "creator": _client_for(creator),
        "editor": _client_for(editor),
        "reviewer": _client_for(reviewer),
        "approver": _client_for(approver),
        "admin": _client_for(admin),
        "viewer": _client_for(viewer),
    }


def test_capability_matrix():
    # Viewer: view only
    assert has_capability(Role.VIEWER, "view_projects")
    assert not has_capability(Role.VIEWER, "manage_projects")
    assert not has_capability(Role.VIEWER, "approve")
    assert not has_capability(Role.VIEWER, "publish")
    # Editor: manage but never approve/publish
    assert has_capability(Role.EDITOR, "manage_projects")
    assert not has_capability(Role.EDITOR, "approve")
    assert not has_capability(Role.EDITOR, "publish")
    # Reviewer: review only, cannot manage/approve/publish
    assert not has_capability(Role.REVIEWER, "manage_projects")
    assert not has_capability(Role.REVIEWER, "approve")
    assert not has_capability(Role.REVIEWER, "publish")
    # Approver/Owner and Admin: may approve and publish
    assert has_capability(Role.APPROVER_OWNER, "approve")
    assert has_capability(Role.APPROVER_OWNER, "publish")
    assert has_capability(Role.ADMIN, "approve")
    assert has_capability(Role.ADMIN, "publish")


def test_viewer_cannot_manage_shared_project(rbac_clients):
    client = rbac_clients["viewer"]
    resp = client.post("/api/projects/", {"topic": "nope"})
    assert resp.status_code == 403
    # A project created by the creator is visible to the viewer (view) but not manageable.
    created = rbac_clients["creator"].post("/api/projects/", {"topic": "shared topic"}).json()
    pid = created["data"]["project"]["id"]
    live = rbac_clients["viewer"].get(f"/api/projects/{pid}/")
    assert live.status_code == 200  # viewer may view
    arch = rbac_clients["viewer"].post(f"/api/projects/{pid}/archive/")
    assert arch.status_code == 403  # viewer cannot manage


def test_editor_can_manage_but_not_approve_or_publish(rbac_clients):
    pid = rbac_clients["creator"].post("/api/projects/", {"topic": "editor topic"}).json()["data"]["project"]["id"]
    arch = rbac_clients["editor"].post(f"/api/projects/{pid}/archive/")
    assert arch.status_code == 200  # editor may manage
    # No publishing endpoint exists in the foundation; publishing is blocked by
    # the capability matrix and structural absence (see guardrail test).


def test_approver_and_admin_can_manage(rbac_clients):
    pid = rbac_clients["creator"].post("/api/projects/", {"topic": "approver topic"}).json()["data"]["project"]["id"]
    assert rbac_clients["approver"].post(f"/api/projects/{pid}/archive/").status_code == 200
    pid2 = rbac_clients["creator"].post("/api/projects/", {"topic": "admin topic"}).json()["data"]["project"]["id"]
    assert rbac_clients["admin"].post(f"/api/projects/{pid2}/archive/").status_code == 200
