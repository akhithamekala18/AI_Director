# -*- coding: utf-8 -*-
"""Gate 4 dependency enforcement (Task 25: media only from APPROVED scenes).

The server must reject media generation from draft / review /
revision_requested scene packages, never trusting any client-supplied state.
"""
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.ai_orchestration.models import AsyncJob
from apps.scene.models import SceneBuilder
from apps.scene_media import services
from apps.scene_media.models import SceneMedia

from .helpers import (
    approved_scene_builder,
    draft_scene_builder,
    make_project,
    review_scene_builder,
    revision_scene_builder,
)


@pytest.mark.django_db
class TestGate4Dependency:
    def test_approved_scene_allows_generation(self, make_user):
        user = make_user(username="gate4_ok")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = services.request_scene_media(user, project)
        job.refresh_from_db()
        assert job.job_type == AsyncJob.JobType.SCENE_MEDIA_GENERATION
        assert job.status == AsyncJob.Status.COMPLETED  # eager run
        assert SceneMedia.objects.filter(project=project).count() == 8

    def test_draft_scene_rejected(self, make_user):
        user = make_user(username="gate4_draft")
        project = make_project(user)
        draft_scene_builder(user, project)
        with pytest.raises(DjangoValidationError) as exc:
            services.request_scene_media(user, project)
        assert "approved scene package" in str(exc.value)
        assert SceneMedia.objects.filter(project=project).count() == 0

    def test_review_scene_rejected(self, make_user):
        user = make_user(username="gate4_review")
        project = make_project(user)
        review_scene_builder(user, project)
        with pytest.raises(DjangoValidationError) as exc:
            services.request_scene_media(user, project)
        assert "approved scene package" in str(exc.value)
        assert SceneMedia.objects.filter(project=project).count() == 0

    def test_revision_requested_scene_rejected(self, make_user):
        user = make_user(username="gate4_revision")
        project = make_project(user)
        revision_scene_builder(user, project)
        with pytest.raises(DjangoValidationError) as exc:
            services.request_scene_media(user, project)
        assert "approved scene package" in str(exc.value)
        assert SceneMedia.objects.filter(project=project).count() == 0

    def test_approved_empty_package_rejected(self, make_user):
        user = make_user(username="gate4_empty")
        project = make_project(user)
        SceneBuilder.objects.create(
            project=project, team=project.team, gate_state=SceneBuilder.GateState.APPROVED
        )
        # gate is approved but there are no scenes to produce media for
        with pytest.raises(DjangoValidationError) as exc:
            services.request_scene_media(user, project)
        assert "no scenes" in str(exc.value)

    def test_foreign_member_rejected(self, make_user):
        owner = make_user(username="gate4_owner")
        outsider = make_user(username="gate4_outsider")
        project = make_project(owner)
        approved_scene_builder(owner, project)
        with pytest.raises(DjangoValidationError) as exc:
            services.request_scene_media(outsider, project)
        assert "not a member" in str(exc.value)


@pytest.mark.django_db
class TestExecutorGateCheck:
    def test_handler_fails_when_gate_not_approved(self, make_user):
        from apps.scene_media.tasks import run_scene_media_generation

        user = make_user(username="exec_gate")
        project = make_project(user)
        builder = review_scene_builder(user, project)
        job = AsyncJob.objects.create(
            team=project.team, project=project, owner=user,
            job_type=AsyncJob.JobType.SCENE_MEDIA_GENERATION,
        )
        assert builder.gate_state == SceneBuilder.GateState.REVIEW
        with pytest.raises(DjangoValidationError):
            run_scene_media_generation(job)
        assert SceneMedia.objects.filter(project=project).count() == 0
