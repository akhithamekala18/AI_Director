# -*- coding: utf-8 -*-
"""Scene Builder service tests (Phase 2E, Task 24).

Covers the Gate 4 service orchestration: build prerequisites (approved Script
Gate 2 + approved Character set Gate 3), build -> review, review -> approved,
review -> revision_requested (reason required), state gating on build/approve,
and team isolation.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.scene import services
from apps.scene.models import SceneBuilder

from .helpers import approved_characters, approved_script, make_project


class TestBuildScenes:
    def test_build_requires_both_gates(self, make_user):
        user = make_user(username="svc_build1")
        project = make_project(user)
        with pytest.raises(ValidationError):
            services.build_scenes(user, project)

    def test_build_requires_approved_character_set(self, make_user):
        user = make_user(username="svc_build2")
        project = make_project(user)
        approved_script(user, project)
        with pytest.raises(ValidationError):
            services.build_scenes(user, project)

    def test_build_moves_to_review_with_scenes(self, make_user):
        user = make_user(username="svc_build3")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)

        builder = services.build_scenes(user, project)
        assert builder.gate_state == SceneBuilder.GateState.REVIEW
        assert len(builder.scenes) == 2
        assert len(builder.scenes[0]["characters"]) >= 1
        assert builder.scenes[0]["id"] == "s1"

    def test_build_when_already_review_is_rejected(self, make_user):
        user = make_user(username="svc_build4")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        services.build_scenes(user, project)
        with pytest.raises(ValidationError):
            services.build_scenes(user, project)


class TestApproveSceneBuilder:
    def test_approve_requires_review_state(self, make_user):
        user = make_user(username="svc_app1")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        builder = services.build_scenes(user, project)

        services.approve_scene_builder(user, builder)
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.APPROVED
        assert builder.approval_actor_id == user.id
        assert builder.approval_at is not None

    def test_approve_after_approval_is_rejected(self, make_user):
        user = make_user(username="svc_app2")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        builder = services.build_scenes(user, project)
        services.approve_scene_builder(user, builder)
        with pytest.raises(ValidationError):
            services.approve_scene_builder(user, builder)


class TestRequestSceneChanges:
    def test_request_changes_requires_reason(self, make_user):
        user = make_user(username="svc_req1")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        builder = services.build_scenes(user, project)
        with pytest.raises(ValidationError):
            services.request_scene_changes(user, builder, "   ")

    def test_request_changes_moves_to_revision(self, make_user):
        user = make_user(username="svc_req2")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        builder = services.build_scenes(user, project)

        services.request_scene_changes(user, builder, "tighten pacing")
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.REVISION_REQUESTED
        assert builder.rejection_reason == "tighten pacing"


class TestTeamIsolation:
    def test_outsider_cannot_read_scene_builder(self, make_user):
        from apps.accounts.models import Team

        owner = make_user(username="iso_owner")
        outsider = make_user(username="iso_out", role="Editor")
        other_team = Team.objects.create(name="Other Team")
        outsider.memberships.create(team=other_team, role="Editor")

        project = make_project(owner)
        script = approved_script(owner, project)
        approved_characters(owner, project, script)
        services.build_scenes(owner, project)

        assert services.get_scene_builder(outsider, project) is None
