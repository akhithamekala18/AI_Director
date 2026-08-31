# -*- coding: utf-8 -*-
"""Thumbnail service tests (Task 36)."""
import pytest
from django.core.exceptions import ValidationError

from apps.thumbnail.models import ThumbnailAsset


@pytest.mark.django_db
class TestThumbnailServices:
    """Unit tests for thumbnail service layer."""

    def test_request_thumbnail_requires_gate4(self, user, project):
        from apps.thumbnail.services import request_thumbnail
        with pytest.raises(ValidationError, match="Gate 4"):
            request_thumbnail(user, project, "YouTube", "Test")

    def test_request_thumbnail_requires_membership(self, outsider_client, project):
        from apps.thumbnail.services import request_thumbnail
        with pytest.raises(ValidationError, match="not a member"):
            request_thumbnail(outsider_client.user, project, "YouTube", "Test")

    def test_list_thumbnails_scoped_to_team(self, auth_client, project, approved_scene_builder):
        from apps.thumbnail.services import list_thumbnails
        auth_client.post(
            f"/api/projects/{project.id}/thumbnail/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        thumbs = list_thumbnails(auth_client.user, project)
        assert thumbs.count() == 1

    def test_get_thumbnail_returns_none_for_outsider(self, auth_client, project, approved_scene_builder, outsider_client):
        from apps.thumbnail.services import request_thumbnail, get_thumbnail
        thumb = request_thumbnail(auth_client.user, project, "YouTube", "Test")
        result = get_thumbnail(outsider_client.user, thumb.id)
        assert result is None
