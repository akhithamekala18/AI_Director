# -*- coding: utf-8 -*-
"""Regeneration model tests: creation, defaults, state machine, lineage."""
import pytest

from apps.regeneration.models import RegenerationRequest, SceneMediaVersion
from apps.scene_media.models import SceneMedia

from .helpers import make_project, setup_media


@pytest.mark.django_db
class TestRegenerationRequestModel:
    def test_create_request(self, make_user):
        user = make_user(username="model_create")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, scene_builder=builder,
            created_by=user, scene_id="s1", media_types=["voice"],
        )
        assert req.pk
        assert req.status == RegenerationRequest.Status.PENDING
        assert req.scene_id == "s1"
        assert req.media_types == ["voice"]
        assert req.full is False

    def test_str(self, make_user):
        user = make_user(username="model_str")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user,
            scene_builder=builder, scene_id="s1",
        )
        assert "s1" in str(req)
        assert "pending" in str(req)


@pytest.mark.django_db
class TestStateMachine:
    def test_pending_to_running(self, make_user):
        user = make_user(username="sm_p2r")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user, scene_builder=builder,
        )
        req.transition_to(RegenerationRequest.Status.RUNNING)
        assert req.status == RegenerationRequest.Status.RUNNING

    def test_completed_is_terminal(self, make_user):
        user = make_user(username="sm_c")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user, scene_builder=builder,
            status=RegenerationRequest.Status.COMPLETED,
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            req.transition_to(RegenerationRequest.Status.RUNNING)


@pytest.mark.django_db
class TestSceneMediaVersionModel:
    def test_create_snapshot(self, make_user):
        user = make_user(username="snap_create")
        project = make_project(user)
        setup_media(user, project)
        builder = getattr(project, "scene_builder", None)
        req = RegenerationRequest.objects.create(
            project=project, team=project.team, created_by=user,
            scene_builder=builder, scene_id="s1",
        )
        media = SceneMedia.objects.filter(project=project, scene_id="s1").first()
        snap = SceneMediaVersion.objects.create(
            media=media, regeneration=req, version=media.version,
            media_type=media.media_type, scene_id=media.scene_id,
            scene_order=media.scene_order, asset_ref=media.asset_ref,
            provider=media.provider, provider_metadata=media.provider_metadata,
            direction=media.direction, narration=media.narration,
            characters=media.characters, duration_seconds=media.duration_seconds,
            pacing=media.pacing, transition=media.transition,
            voice=media.voice, music=media.music, caption=media.caption,
        )
        assert snap.pk
        assert snap.version == media.version
