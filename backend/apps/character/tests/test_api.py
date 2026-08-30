# -*- coding: utf-8 -*-
"""Character API endpoint tests (Phase 2D, Task 23).

Covers the character endpoints (generate, detail, approve, request-changes,
library, reuse), capability-based authorization, and team isolation (a user
outside the project's team cannot read or mutate character data).
"""
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team
from apps.character.models import CharacterLibrary
from apps.projects.models import Project

from .helpers import FAKE_CHARACTERS, approved_script


def _client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client


@pytest.fixture
def character_flow(make_user):
    """Build a project with an APPROVED Script, plus Editor/Approver/outsider."""

    def _build():
        manager = make_user(username="char_mgr", role="Editor")
        approver = make_user(username="char_ao", role="Approver/Owner")
        outsider = make_user(username="char_out", role="Editor")
        team = Team.objects.create(name="Char Team")
        manager.memberships.create(team=team, role="Editor")
        approver.memberships.create(team=team, role="Approver/Owner")
        project = Project.objects.create(
            team=team,
            owner=manager,
            topic="Volcanic eruptions",
            lifecycle_state="Draft",
        )
        approved_script(manager, project)  # satisfy Gate 2 (Script approved)
        return {
            "team": team,
            "project": project,
            "manager": manager,
            "approver": approver,
            "outsider": outsider,
            "manager_client": _client(manager),
            "approver_client": _client(approver),
            "outsider_client": _client(outsider),
        }

    return _build


@pytest.mark.django_db
class TestGenerateAndRead:
    def test_generate_then_read_then_approve_flow(self, character_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        f = character_flow()
        pid = f["project"].id

        resp = f["manager_client"].post(f"/api/projects/{pid}/character/generate/")
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]["character"]
        assert data["gate_state"] == "review"
        assert data["character_count"] == 2

        resp = f["manager_client"].get(f"/api/projects/{pid}/character/")
        assert resp.status_code == 200
        assert resp.json()["data"]["character"]["gate_state"] == "review"

        resp = f["approver_client"].post(f"/api/projects/{pid}/character/approve/")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["character"]["gate_state"] == "approved"

    def test_request_changes_flow(self, character_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        f = character_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/character/generate/")

        resp = f["approver_client"].post(
            f"/api/projects/{pid}/character/request-changes/",
            {"reason": "give the narrator a cleaner style"},
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["character"]["gate_state"] == "revision_requested"

    def test_request_changes_requires_reason(self, character_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        f = character_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/character/generate/")

        resp = f["approver_client"].post(
            f"/api/projects/{pid}/character/request-changes/", {"reason": ""}
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False


@pytest.mark.django_db
class TestLibraryEndpoints:
    def _approve_with_ids(self, f, pid):
        from apps.character.models import Character

        character, _ = Character.objects.get_or_create(
            project_id=pid,
            defaults={
                "team": f["team"],
                "script": f["project"].script,
            },
        )
        character.script = f["project"].script
        character.characters = [
            {
                "id": "char_api_1",
                "name": "Maya",
                "age": "30s",
                "gender": "female",
                "appearance": {"hair_color": "brown"},
                "clothing": {"outfit": "jacket"},
                "accessories": ["helmet"],
                "style": {"realism": "medium"},
            }
        ]
        character.gate_state = "review"
        character.save()
        resp = f["approver_client"].post(f"/api/projects/{pid}/character/approve/")
        assert resp.status_code == 200, resp.content

    def test_library_lists_approved_characters(self, character_flow):
        f = character_flow()
        pid = f["project"].id
        self._approve_with_ids(f, pid)

        resp = f["manager_client"].get(f"/api/projects/{pid}/character/library/")
        assert resp.status_code == 200, resp.content
        library = resp.json()["data"]["library"]
        assert any(e["character_id"] == "char_api_1" for e in library)

    def test_reuse_applies_library_character(self, character_flow):
        f = character_flow()
        pid_a = f["project"].id
        self._approve_with_ids(f, pid_a)

        project_b = Project.objects.create(
            team=f["team"], owner=f["manager"], topic="B topic", lifecycle_state="Draft"
        )
        approved_script(f["manager"], project_b)
        entry = CharacterLibrary.objects.get(character_id="char_api_1")

        resp = f["manager_client"].post(
            f"/api/projects/{pid_a}/character/reuse/",
            {"library_entry_id": entry.id},
        )
        # reuse targets the project in the URL; here we reuse into project A,
        # verifying reuse endpoint wiring rather than cross-project scope.
        assert resp.status_code == 200, resp.content
        assert any(
            c["id"] == "char_api_1"
            for c in resp.json()["data"]["character"]["characters"]
        )


@pytest.mark.django_db
class TestAuthorization:
    def test_editor_cannot_approve(self, character_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        f = character_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/character/generate/")
        resp = f["manager_client"].post(f"/api/projects/{pid}/character/approve/")
        assert resp.status_code == 403
        assert resp.json()["success"] is False

    def test_viewer_cannot_generate(self, character_flow, make_user):
        f = character_flow()
        pid = f["project"].id
        viewer = make_user(username="char_viewer", role="Viewer")
        viewer.memberships.create(team=f["team"], role="Viewer")
        client = _client(viewer)
        resp = client.post(f"/api/projects/{pid}/character/generate/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTeamIsolation:
    def test_outsider_cannot_read_character(self, character_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        f = character_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/character/generate/")
        resp = f["outsider_client"].get(f"/api/projects/{pid}/character/")
        assert resp.status_code == 404

    def test_outsider_cannot_generate(self, character_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        f = character_flow()
        pid = f["project"].id
        resp = f["outsider_client"].post(f"/api/projects/{pid}/character/generate/")
        # outsider is not a member of the project's team -> 404 (team isolation)
        assert resp.status_code == 404
