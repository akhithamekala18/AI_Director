# -*- coding: utf-8 -*-
"""Research API endpoint tests (R6, step24/07 contract).

Covers the six research endpoints, capability-based authorization, and team
isolation (a user outside the project's team cannot read or mutate research).
"""
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team
from apps.projects.models import Project

from .helpers import FAKE_RESEARCH


def _client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    client.user = user
    return client


@pytest.fixture
def research_flow(make_user):
    """Build a shared-team project with an Editor manager and an Approver."""

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


@pytest.mark.django_db
class TestGenerateAndRead:
    def test_generate_then_read_then_approve_flow(self, research_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        f = research_flow()
        pid = f["project"].id

        # 1. generate (manage_projects)
        resp = f["manager_client"].post(f"/api/projects/{pid}/research/generate/")
        assert resp.status_code == 200, resp.content
        data = resp.json()["data"]["research"]
        assert data["gate_state"] == "review"
        assert data["source_count"] >= 1

        # 2. read summary (view_projects)
        resp = f["manager_client"].get(f"/api/projects/{pid}/research/")
        assert resp.status_code == 200
        assert resp.json()["data"]["research"]["gate_state"] == "review"

        # 3. sources
        resp = f["manager_client"].get(f"/api/projects/{pid}/research/sources/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["sources"]) >= 1

        # 4. gaps
        resp = f["manager_client"].get(f"/api/projects/{pid}/research/gaps/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["gaps"]) == 1

        # 5. approve (approve)
        resp = f["approver_client"].post(f"/api/projects/{pid}/research/approve/")
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["research"]["gate_state"] == "approved"

    def test_request_changes_flow(self, research_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        f = research_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/research/generate/")

        resp = f["approver_client"].post(
            f"/api/projects/{pid}/research/request-changes/",
            {"reason": "add more sources"},
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["research"]["gate_state"] == "revision_requested"

    def test_request_changes_requires_reason(self, research_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        f = research_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/research/generate/")

        resp = f["approver_client"].post(
            f"/api/projects/{pid}/research/request-changes/", {"reason": ""}
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False


@pytest.mark.django_db
class TestAuthorization:
    def test_editor_cannot_approve(self, research_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        f = research_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/research/generate/")
        resp = f["manager_client"].post(f"/api/projects/{pid}/research/approve/")
        assert resp.status_code == 403
        assert resp.json()["success"] is False

    def test_viewer_cannot_generate(self, research_flow, make_user):
        f = research_flow()
        viewer = make_user(username="flow_viewer", role="Viewer")
        viewer.memberships.create(team=f["team"], role="Viewer")
        client = _client(viewer)
        pid = f["project"].id
        resp = client.post(f"/api/projects/{pid}/research/generate/")
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTeamIsolation:
    def test_outsider_cannot_read_research(self, research_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        f = research_flow()
        pid = f["project"].id
        f["manager_client"].post(f"/api/projects/{pid}/research/generate/")
        resp = f["outsider_client"].get(f"/api/projects/{pid}/research/")
        assert resp.status_code == 404

    def test_outsider_cannot_generate(self, research_flow, monkeypatch):
        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        f = research_flow()
        pid = f["project"].id
        resp = f["outsider_client"].post(f"/api/projects/{pid}/research/generate/")
        # outsider is not a member of the project's team -> 404 (team isolation)
        assert resp.status_code == 404
