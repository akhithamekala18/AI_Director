# -*- coding: utf-8 -*-
"""Thumbnail API tests (Task 36).

Uses token-based authentication via APIClient, consistent with the
project's established test patterns (Phase 2E, 2F).
"""
import pytest
from rest_framework.test import APIClient

from apps.thumbnail.models import ThumbnailAsset


@pytest.mark.django_db
class TestThumbnailGenerateAPI:
    """POST /api/projects/{id}/thumbnail/generate/"""

    def test_generate_thumbnail_success(self, auth_client, project, approved_scene_builder):
        resp = auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube", "title_text": "My Video"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["success"] is True
        thumb = data["data"]["thumbnail"]
        assert thumb["status"] == "ready"
        assert thumb["platform_target"] == "YouTube"
        assert thumb["title_text"] == "My Video"
        assert thumb["version"] == 1

    def test_generate_thumbnail_no_gate4(self, auth_client, project):
        """Thumbnail generation requires Gate 4 approval."""
        resp = auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_generate_thumbnail_unauthorized(self, project):
        """Unauthenticated user gets 403 (HasCapability convention)."""
        anon = APIClient()
        resp = anon.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        assert resp.status_code == 403

    def test_generate_thumbnail_idempotent(self, auth_client, project, approved_scene_builder):
        """Generating twice creates only one row (get_or_create), version increments."""
        auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube", "title_text": "My Video"},
            format="json",
        )
        auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube", "title_text": "My Video"},
            format="json",
        )
        assert ThumbnailAsset.objects.filter(project=project).count() == 1
        thumb = ThumbnailAsset.objects.get(project=project)
        assert thumb.version == 2


@pytest.mark.django_db
class TestThumbnailListAPI:
    """GET /api/projects/{id}/thumbnail/"""

    def test_list_thumbnails(self, auth_client, project, approved_scene_builder):
        auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        resp = auth_client.get(f"/api/projects/{project.id}/thumbnail/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]["thumbnails"]) == 1

    def test_list_thumbnails_empty(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/thumbnail/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["thumbnails"]) == 0

    def test_cross_team_access_returns_404(self, outsider_client, auth_client, project, approved_scene_builder):
        """Outsider cannot see another team's thumbnails (404 team isolation)."""
        auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        resp = outsider_client.get(f"/api/projects/{project.id}/thumbnail/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestThumbnailDetailAPI:
    """GET /api/projects/{id}/thumbnail/<thumbnail_id>/"""

    def test_get_thumbnail_detail(self, auth_client, project, approved_scene_builder):
        gen_resp = auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube", "title_text": "Test Thumb"},
            format="json",
        )
        thumb_id = gen_resp.json()["data"]["thumbnail"]["id"]
        resp = auth_client.get(f"/api/projects/{project.id}/thumbnail/{thumb_id}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["thumbnail"]["id"] == thumb_id

    def test_get_thumbnail_not_found(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/thumbnail/99999/")
        assert resp.status_code == 404
