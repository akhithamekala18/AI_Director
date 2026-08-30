# -*- coding: utf-8 -*-
"""API tests for scene media (auth, membership, Gate 4, generation, retrieval)."""
import pytest
from rest_framework.test import APIClient

from .helpers import (
    approved_scene_builder,  # noqa: F401
    make_project,
    review_scene_builder,
)

GENERATE = "/api/projects/{}/scene-media/generate/"
LIST = "/api/projects/{}/scene-media/"


@pytest.mark.django_db
class TestSceneMediaAPI:
    def _project_for(self, client, username, builder="approved"):
        user = client.user
        project = make_project(user)
        if builder == "approved":
            approved_scene_builder(user, project)
        elif builder == "review":
            review_scene_builder(user, project)
        return project

    def test_generate_returns_job_and_media(self, api_client):
        client = api_client(username="api_gen")
        project = self._project_for(client, "api_gen")
        resp = client.post(GENERATE.format(project.id), {}, format="json")
        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["job"]["job_type"] == "scene_media_generation"
        assert data["data"]["job"]["status"] == "completed"  # eager
        media = client.get(LIST.format(project.id)).json()["data"]["media"]
        assert len(media) == 8
        assert {m["media_type"] for m in media} == {"visual", "voice", "music", "subtitle"}

    def test_list_and_detail_membership_success(self, api_client):
        client = api_client(username="api_list")
        project = self._project_for(client, "api_list")
        client.post(GENERATE.format(project.id), {}, format="json")
        media = client.get(LIST.format(project.id)).json()["data"]["media"]
        first = media[0]
        detail = client.get(
            "/api/projects/{}/scene-media/{}/".format(project.id, first["id"])
        ).json()
        assert detail["data"]["media"]["id"] == first["id"]

    def test_anonymous_rejected(self, api_client):
        client = api_client(username="api_anon_src")
        project = self._project_for(client, "api_anon_src")
        anon = APIClient()
        # HasCapability returns Forbidden for an unauthenticated user (the
        # repository's established behavior: anonymous callers are not allowed).
        assert anon.post(GENERATE.format(project.id), {}, format="json").status_code == 403
        assert anon.get(LIST.format(project.id)).status_code == 403

    def test_invalid_gate_state_returns_400(self, api_client):
        client = api_client(username="api_gate")
        project = self._project_for(client, "api_gate", builder="review")
        resp = client.post(GENERATE.format(project.id), {}, format="json")
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_cross_team_access_returns_404(self, api_client):
        member = api_client(username="api_member")
        outsider = api_client(username="api_outsider")
        project = self._project_for(member, "api_member")
        # outsider hits member's project -> 404 (no existence leak)
        assert outsider.post(GENERATE.format(project.id), {}, format="json").status_code == 404
        assert outsider.get(LIST.format(project.id)).status_code == 404

    def test_viewer_cannot_generate_returns_403(self, api_client):
        viewer = api_client(username="api_viewer", role="Viewer")
        project = self._project_for(viewer, "api_viewer")
        resp = viewer.post(GENERATE.format(project.id), {}, format="json")
        assert resp.status_code == 403
