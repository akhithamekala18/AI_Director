# -*- coding: utf-8 -*-
"""Video API tests (Task 36).

Uses token-based authentication via APIClient, consistent with the
project's established test patterns (Phase 2E, 2F).
"""
import pytest
from rest_framework.test import APIClient

from apps.video.models import VideoAsset


@pytest.mark.django_db
class TestVideoGenerateAPI:
    """POST /api/projects/{id}/video/generate/"""

    def test_generate_video_success(self, auth_client, project, approved_scene_builder):
        resp = auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["success"] is True
        video = data["data"]["video"]
        assert video["status"] == "ready"
        assert video["platform_target"] == "YouTube"
        assert video["scene_count"] == 2
        assert video["version"] == 1

    def test_generate_video_no_gate4(self, auth_client, project):
        """Video generation requires Gate 4 approval."""
        resp = auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_generate_video_unauthorized(self, project):
        """Unauthenticated user gets 403 (HasCapability convention)."""
        anon = APIClient()
        resp = anon.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        assert resp.status_code == 403

    def test_generate_video_idempotent(self, auth_client, project, approved_scene_builder):
        """Generating twice creates only one row (get_or_create), version increments."""
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        assert VideoAsset.objects.filter(project=project).count() == 1
        video = VideoAsset.objects.get(project=project)
        assert video.version == 2

    def test_generate_video_different_platforms(self, auth_client, project, approved_scene_builder):
        """Different platforms create separate video rows."""
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "TikTok"},
            format="json",
        )
        assert VideoAsset.objects.filter(project=project).count() == 2


@pytest.mark.django_db
class TestVideoListAPI:
    """GET /api/projects/{id}/video/"""

    def test_list_videos(self, auth_client, project, approved_scene_builder):
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        resp = auth_client.get(f"/api/projects/{project.id}/video/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["videos"]) == 1

    def test_list_videos_empty(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/video/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["videos"]) == 0

    def test_cross_team_access_returns_404(self, outsider_client, auth_client, project, approved_scene_builder):
        """Outsider cannot see another team's videos (404 team isolation)."""
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        resp = outsider_client.get(f"/api/projects/{project.id}/video/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestVideoDetailAPI:
    """GET /api/projects/{id}/video/<video_id>/"""

    def test_get_video_detail(self, auth_client, project, approved_scene_builder):
        gen_resp = auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        video_id = gen_resp.json()["data"]["video"]["id"]
        resp = auth_client.get(f"/api/projects/{project.id}/video/{video_id}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["video"]["id"] == video_id

    def test_get_video_not_found(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/video/99999/")
        assert resp.status_code == 404
