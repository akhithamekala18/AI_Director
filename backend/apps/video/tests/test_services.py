# -*- coding: utf-8 -*-
"""Video service tests (Task 36)."""
import pytest
from django.core.exceptions import ValidationError

from apps.video.models import VideoAsset


@pytest.mark.django_db
class TestVideoServices:
    """Unit tests for video service layer."""

    def test_request_video_requires_gate4(self, user, project):
        from apps.video.services import request_video
        with pytest.raises(ValidationError, match="Gate 4"):
            request_video(user, project, "YouTube")

    def test_request_video_requires_membership(self, outsider_client, project):
        from apps.video.services import request_video
        with pytest.raises(ValidationError, match="not a member"):
            request_video(outsider_client.user, project, "YouTube")

    def test_list_videos_scoped_to_team(self, auth_client, project, approved_scene_builder):
        from apps.video.services import list_videos
        auth_client.post(
            f"/api/projects/{project.id}/video/generate/",
            data={"platform_target": "YouTube"},
            format="json",
        )
        videos = list_videos(auth_client.user, project)
        assert videos.count() == 1

    def test_get_video_returns_none_for_outsider(self, auth_client, project, approved_scene_builder, outsider_client):
        from apps.video.services import request_video, get_video
        video = request_video(auth_client.user, project, "YouTube")
        result = get_video(outsider_client.user, video.id)
        assert result is None
