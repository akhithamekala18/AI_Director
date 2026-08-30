# -*- coding: utf-8 -*-
"""Script API endpoint tests (R6, Development Plan Day 22).

Covers the script endpoints, capability-based authorization, and team isolation
(a user outside the project's team cannot read or mutate scripts).
"""
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team
from apps.projects.models import Project

from .helpers import FAKE_SCRIPT


def _client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client


@pytest.fixture
def script_flow(make_user, monkeypatch):
    """Build a project with approved research, an Editor and an Approver."""

    monkeypatch.setattr(
        "apps.research.engine.gather_research",
        lambda project: {
            "summary": "Quantum gravity reconciles general relativity with quantum "
            "mechanics.",
            "sources": [
                {
                    "url": "https://example.org/quantum-gravity",
                    "title": "Quantum Gravity Explained",
                    "snippet": "An overview of quantum gravity research.",
                    "credibility_score": 0.9,
                }
            ],
            "gaps": [
                {
                    "gap_type": "contradiction",
                    "description": "Two sources disagree on the role of time.",
                    "source_a": "A",
                    "source_b": "B",
                }
            ],
            "cost": 0.03,
        },
    )

    def _build():
        manager = make_user(username="flow_mgr", role="Editor")
        approver = make_user(username="flow_ao", role="Approver/Owner")
        outsider = make_user(username="flow_out", role="Editor")
        team = Team.objects.create(name="Shared Team")
        manager.memberships.create(team=team, role="Editor")
        approver.memberships.create(team=team, role="Approver/Owner")
        project = Project.objects.create(
            team=team,
            owner=manager,
            topic="Quantum gravity",
            lifecycle_state="Draft",
        )
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


def _approve_research(f):
    """Generate + approve research via the research API so G-1 is satisfied."""
    pid = f["project"].id
    f["manager_client"].post(f"/api/projects/{pid}/research/generate/")
    resp = f["approver_client"].post(f"/api/projects/{pid}/research/approve/")
    assert resp.status_code == 200, resp.content
    return pid


@pytest.mark.django_db
class TestGenerateAndRead:
    def test_generate_then_read_then_approve_flow(self, script_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        f = script_flow()
        pid = _approve_research(f)

        # 1. generate script (manage_projects)
        resp = f["manager_client"].post(f"/api/projects/{pid}/script/generate/")
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]["script"]
        assert data["gate_state"] == "review"
        assert data["title"] == "Quantum Gravity Explained"
        assert data["scene_count"] == 2

        # 2. read script package (view_projects)
        resp = f["manager_client"].get(f"/api/projects/{pid}/script/")
        assert resp.status_code == 200
        assert resp.json()["data"]["script"]["gate_state"] == "review"
        assert resp.json()["data"]["script"]["hashtags"] == [
            "#quantumgravity",
            "#physics",
        ]

        # 3. approve (approve)
        resp = f["approver_client"].post(f"/api/projects/{pid}/script/approve/")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["script"]["gate_state"] == "approved"

    def test_request_changes_flow(self, script_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        f = script_flow()
        pid = _approve_research(f)
        f["manager_client"].post(f"/api/projects/{pid}/script/generate/")

        resp = f["approver_client"].post(
            f"/api/projects/{pid}/script/request-changes/",
            {"reason": "tighten the script"},
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["script"]["gate_state"] == "revision_requested"

    def test_request_changes_requires_reason(self, script_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        f = script_flow()
        pid = _approve_research(f)
        f["manager_client"].post(f"/api/projects/{pid}/script/generate/")

        resp = f["approver_client"].post(
            f"/api/projects/{pid}/script/request-changes/", {"reason": ""}
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False


@pytest.mark.django_db
class TestAuthorization:
    def test_editor_cannot_approve(self, script_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        f = script_flow()
        pid = _approve_research(f)
        f["manager_client"].post(f"/api/projects/{pid}/script/generate/")
        resp = f["manager_client"].post(f"/api/projects/{pid}/script/approve/")
        assert resp.status_code == 403
        assert resp.json()["success"] is False

    def test_viewer_cannot_generate(self, script_flow, make_user):
        from .helpers import approved_research

        f = script_flow()
        pid = f["project"].id
        approved_research(f["manager"], f["project"])
        viewer = make_user(username="flow_viewer", role="Viewer")
        viewer.memberships.create(team=f["team"], role="Viewer")
        client = _client(viewer)
        resp = client.post(f"/api/projects/{pid}/script/generate/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTeamIsolation:
    def test_outsider_cannot_read_script(self, script_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        f = script_flow()
        pid = _approve_research(f)
        f["manager_client"].post(f"/api/projects/{pid}/script/generate/")
        resp = f["outsider_client"].get(f"/api/projects/{pid}/script/")
        assert resp.status_code == 404

    def test_outsider_cannot_generate(self, script_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        f = script_flow()
        pid = _approve_research(f)
        resp = f["outsider_client"].post(f"/api/projects/{pid}/script/generate/")
        # outsider is not a member of the project's team -> 404 (team isolation)
        assert resp.status_code == 404
