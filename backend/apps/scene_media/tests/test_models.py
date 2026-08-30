# -*- coding: utf-8 -*-
"""SceneMedia model tests: creation, status choices, unique constraint."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.scene_media.models import SceneMedia

from .helpers import approved_scene_builder, make_project


@pytest.mark.django_db
class TestSceneMediaModel:
    def test_create_media_row(self, make_user):
        user = make_user(username="media_model")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        media = SceneMedia.objects.create(
            project=project,
            team=project.team,
            scene_builder=builder,
            scene_id="s1",
            scene_order=1,
            media_type=SceneMedia.MediaType.VOICE,
            status=SceneMedia.Status.READY,
            asset_ref="mock://voice/s1",
        )
        assert media.pk
        assert media.status == "ready"
        assert str(media) == "voice@s1 (ready)"

    def test_default_status_is_pending(self, make_user):
        user = make_user(username="media_default")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        media = SceneMedia.objects.create(
            project=project,
            team=project.team,
            scene_builder=builder,
            scene_id="s2",
            media_type=SceneMedia.MediaType.VISUAL,
        )
        assert media.status == SceneMedia.Status.PENDING

    def test_unique_constraint_per_scene_type(self, make_user):
        user = make_user(username="media_unique")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        SceneMedia.objects.create(
            project=project,
            team=project.team,
            scene_builder=builder,
            scene_id="s1",
            media_type=SceneMedia.MediaType.VOICE,
        )
        with pytest.raises(IntegrityError):
            SceneMedia.objects.create(
                project=project,
                team=project.team,
                scene_builder=builder,
                scene_id="s1",
                media_type=SceneMedia.MediaType.VOICE,
            )

    def test_different_media_type_allowed_same_scene(self, make_user):
        user = make_user(username="media_types")
        project = make_project(user)
        builder = approved_scene_builder(user, project)
        SceneMedia.objects.create(
            project=project,
            team=project.team,
            scene_builder=builder,
            scene_id="s1",
            media_type=SceneMedia.MediaType.VOICE,
        )
        SceneMedia.objects.create(
            project=project,
            team=project.team,
            scene_builder=builder,
            scene_id="s1",
            media_type=SceneMedia.MediaType.MUSIC,
        )
        assert SceneMedia.objects.filter(scene_id="s1").count() == 2

    def test_required_fields_enforced(self, make_user):
        user = make_user(username="media_required")
        project = make_project(user)
        media = SceneMedia(project=project, team=project.team)
        with pytest.raises(ValidationError):
            media.full_clean()
