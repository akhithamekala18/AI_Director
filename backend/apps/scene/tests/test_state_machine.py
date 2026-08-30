# -*- coding: utf-8 -*-
"""Gate 4 state machine tests (Phase 2E, Task 24 / Overview §20.1.6, §23.2).

Validates the SceneBuilder model's transition rules and service-layer gate
validation:
  draft -> review            [sync build; G-2 + G-3: approved Script AND
                              approved Character set required],
  review -> approved         (at least one scene required),
  review -> revision_requested (reason required),
  revision_requested -> review  (rebuild).
"""
import pytest
from django.core.exceptions import ValidationError

from apps.character.models import Character
from apps.scene import services
from apps.scene.models import SceneBuilder, can_build_scenes

from .helpers import approved_characters, approved_script, make_project


class TestStateMachineTransitions:
    def test_legal_transitions_function(self):
        tr = SceneBuilder._TRANSITIONS
        assert tr[SceneBuilder.GateState.DRAFT] == {SceneBuilder.GateState.REVIEW}
        assert tr[SceneBuilder.GateState.REVIEW] == {
            SceneBuilder.GateState.APPROVED,
            SceneBuilder.GateState.REVISION_REQUESTED,
        }
        assert tr[SceneBuilder.GateState.APPROVED] == set()
        assert tr[SceneBuilder.GateState.REVISION_REQUESTED] == {
            SceneBuilder.GateState.REVIEW
        }

    def test_illegal_transition_raises(self):
        builder = SceneBuilder(project=None, team=None)
        builder.gate_state = SceneBuilder.GateState.DRAFT
        with pytest.raises(ValueError):
            builder.transition_to(SceneBuilder.GateState.APPROVED)

    def test_same_state_transition_is_illegal(self):
        builder = SceneBuilder(project=None, team=None)
        builder.gate_state = SceneBuilder.GateState.REVIEW
        with pytest.raises(ValueError):
            builder.transition_to(SceneBuilder.GateState.REVIEW)


class TestGateChainDependency:
    def test_requires_approved_script(self, make_user):
        user = make_user(username="g4_scene1")
        project = make_project(user)
        chars = approved_characters(user, project)
        builder = SceneBuilder(
            project=project, team=project.team, character_set=chars, script=None
        )
        ok, err = can_build_scenes(builder)
        assert ok is False
        assert "script" in err.lower()

    def test_requires_approved_characters(self, make_user):
        user = make_user(username="g4_scene2")
        project = make_project(user)
        script = approved_script(user, project)
        builder = SceneBuilder(project=project, team=project.team, script=script)
        ok, err = can_build_scenes(builder)
        assert ok is False
        assert ("character" in err.lower()) or ("character" in err)

    def test_rejects_unapproved_character_set(self, make_user):
        user = make_user(username="g4_scene3")
        project = make_project(user)
        script = approved_script(user, project)
        raw = Character.objects.create(
            project=project, team=project.team, script=script, gate_state="review"
        )
        builder = SceneBuilder(
            project=project, team=project.team, script=script, character_set=raw
        )
        ok, _err = can_build_scenes(builder)
        assert ok is False

    def test_approved_script_and_characters_allow_building(self, make_user):
        user = make_user(username="g4_scene4")
        project = make_project(user)
        script = approved_script(user, project)
        chars = approved_characters(user, project, script)
        builder = SceneBuilder(
            project=project, team=project.team, script=script, character_set=chars
        )
        ok, _err = can_build_scenes(builder)
        assert ok is True

    def test_no_build_without_approved_prerequisites_via_service(self, make_user):
        user = make_user(username="g4_scene5")
        project = make_project(user)
        with pytest.raises(ValidationError):
            services.build_scenes(user, project)


class TestGate4RevisionCycle:
    def test_build_then_review_then_approve(self, make_user):
        user = make_user(username="g4_rev")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)

        builder = services.build_scenes(user, project)
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.REVIEW
        assert len(builder.scenes) == 2
        v1 = builder.version
        assert v1 == 2

        services.approve_scene_builder(user, builder)
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.APPROVED

    def test_revision_cycle_preserves_scene_ids(self, make_user):
        user = make_user(username="g4_rev2")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)

        builder = services.build_scenes(user, project)
        builder.refresh_from_db()
        scene_ids = [s["id"] for s in builder.scenes]
        assert scene_ids == ["s1", "s2"]

        services.request_scene_changes(user, builder, "tighten the outro")
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.REVISION_REQUESTED

        services.build_scenes(user, project)
        builder.refresh_from_db()
        assert builder.gate_state == SceneBuilder.GateState.REVIEW
        assert builder.version == 3
        assert [s["id"] for s in builder.scenes] == scene_ids
