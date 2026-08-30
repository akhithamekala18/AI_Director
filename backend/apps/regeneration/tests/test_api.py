# -*- coding: utf-8 -*-
"""API tests for regeneration: auth, membership, Gate 4, creation, retrieval."""
import pytest
from rest_framework.test import APIClient

from .helpers import make_project, setup_media

REGEN_LIST = "/api/projects/{}/regeneration/"
REGEN_CREATE = "/api/projects/{}/regeneration/regenerate/"
REGEN_DETAIL = "/api/projects/{}/regeneration/{}/"


@pytest.mark.django_db
class TestRegenerationAPI:
    def _setup_project(self, client, username):
        user = client.user
        project = make_project(user)
        setup_media(user, project)
        return project

    def test_create_regeneration_returns_202(self, api_client):
        client = api_client(username="api_create")
        project = self._setup_project(client, "api_create")
        resp = client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["job"]["job_type"] == "regeneration"
        assert data["data"]["job"]["status"] == "completed"

    def test_list_regenerations(self, api_client):
        client = api_client(username="api_list")
        project = self._setup_project(client, "api_list")
        client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        resp = client.get(REGEN_LIST.format(project.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["regeneration"]) >= 1

    def test_detail_regeneration(self, api_client):
        client = api_client(username="api_detail")
        project = self._setup_project(client, "api_detail")
        client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        from apps.regeneration import services
        req = services.list_regeneration_requests(client.user, project).first()
        resp = client.get(REGEN_DETAIL.format(project.id, req.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["regeneration"]["id"] == req.id

    def test_anonymous_rejected(self, api_client):
        client = api_client(username="api_anon_src")
        project = self._setup_project(client, "api_anon_src")
        anon = APIClient()
        assert anon.post(
            REGEN_CREATE.format(project.id), {}, format="json"
        ).status_code == 403
        assert anon.get(REGEN_LIST.format(project.id)).status_code == 403

    def test_cross_team_returns_404(self, api_client):
        member = api_client(username="api_member")
        outsider = api_client(username="api_outsider")
        project = self._setup_project(member, "api_member")
        assert outsider.post(
            REGEN_CREATE.format(project.id), {}, format="json"
        ).status_code == 404
        assert outsider.get(REGEN_LIST.format(project.id)).status_code == 404

    def test_invalid_gate_state_returns_400(self, api_client):
        from apps.scene import services as scene_services
        from apps.scene.tests.helpers import approved_characters, approved_script
        client = api_client(username="api_gate")
        user = client.user
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        scene_services.build_scenes(user, project)
        resp = client.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_viewer_cannot_generate(self, api_client):
        viewer = api_client(username="api_viewer", role="Viewer")
        project = self._setup_project(viewer, "api_viewer")
        resp = viewer.post(
            REGEN_CREATE.format(project.id),
            {"scene_id": "s1", "media_types": ["voice"]},
            format="json",
        )
        assert resp.status_code == 403

    def test_missing_scene_id_for_non_full_returns_400(self, api_client):
        client = api_client(username="api_noscene")
        project = self._setup_project(client, "api_noscene")
        resp = client.post(
            REGEN_CREATE.format(project.id),
            {"media_types": ["voice"]},
            format="json",
        )
        assert resp.status_code == 400

    def test_full_regeneration_accepted(self, api_client):
        client = api_client(username="api_full")
        project = self._setup_project(client, "api_full")
        resp = client.post(
            REGEN_CREATE.format(project.id),
            {"full": True},
            format="json",
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["data"]["job"]["status"] == "completed"
