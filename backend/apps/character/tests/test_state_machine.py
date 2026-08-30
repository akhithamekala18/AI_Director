# -*- coding: utf-8 -*-
"""Gate 3 state machine tests (Phase 2D, Task 23 / Overview §20.1.4).

Validates the Character model's transition rules and the service-layer gate
validation:
  draft->generating (G-2: approved Script required),
  generating->review (at least one character required),
  review->approved (at least one character required),
  review->revision_requested (reason required),
  revision_requested->generating (previous version preserved).
"""
import pytest
from django.core.exceptions import ValidationError

from apps.character import services
from apps.character.models import Character, can_generate_characters

from .helpers import FAKE_CHARACTERS, approved_script, make_project


class TestStateMachineTransitions:
    def test_legal_transitions_function(self):
        tr = Character._TRANSITIONS
        assert tr[Character.GateState.DRAFT] == {Character.GateState.GENERATING}
        assert tr[Character.GateState.GENERATING] == {Character.GateState.REVIEW}
        assert tr[Character.GateState.REVIEW] == {
            Character.GateState.APPROVED,
            Character.GateState.REVISION_REQUESTED,
        }
        assert tr[Character.GateState.APPROVED] == set()
        assert tr[Character.GateState.REVISION_REQUESTED] == {
            Character.GateState.GENERATING
        }

    def test_illegal_transition_raises(self, make_user):
        character = Character(project=None, team=None)
        character.gate_state = Character.GateState.DRAFT
        with pytest.raises(ValueError):
            character.transition_to(Character.GateState.APPROVED)

    def test_same_state_transition_is_illegal(self, make_user):
        character = Character(project=None, team=None)
        character.gate_state = Character.GateState.REVIEW
        with pytest.raises(ValueError):
            character.transition_to(Character.GateState.REVIEW)


class TestG2ScriptDependency:
    def test_can_generate_characters_requires_approved_script(self, make_user):
        user = make_user(username="g2_char")
        project = make_project(user)
        character = Character(project=project, team=project.team, script=None)
        ok, err = can_generate_characters(character)
        assert ok is False
        assert "approved" in err.lower() or "script" in err.lower()

    def test_can_generate_characters_rejects_unapproved_script(self, make_user):
        from apps.script.models import Script

        user = make_user(username="g2_char2")
        project = make_project(user)
        script = Script.objects.create(
            project=project,
            team=project.team,
            title="V",
            script="body",
            narration="n",
            gate_state=Script.GateState.REVIEW,
        )
        character = Character(project=project, team=project.team, script=script)
        ok, err = can_generate_characters(character)
        assert ok is False

    def test_approved_script_allows_detection(self, make_user):
        user = make_user(username="g2_char3")
        project = make_project(user)
        script = approved_script(user, project)
        character = Character(project=project, team=project.team, script=script)
        ok, err = can_generate_characters(character)
        assert ok is True

    def test_no_detection_without_approved_script_via_service(self, make_user):
        user = make_user(username="g2_char4")
        project = make_project(user)
        with pytest.raises(ValidationError):
            services.generate_characters(user, project)


class TestGate3RevisionCycle:
    def test_previous_version_preserved_on_regeneration(self, make_user, monkeypatch):
        from apps.character.models import Character
        from apps.character.services import request_character_changes

        monkeypatch.setattr(
            "apps.character.engine.detect_characters",
            lambda script, provider=None, existing_ids=(): dict(FAKE_CHARACTERS),
        )
        user = make_user(username="rev_char")
        project = make_project(user)
        approved_script(user, project)

        services.generate_characters(user, project)
        character = Character.objects.get(project=project)
        character.refresh_from_db()
        assert character.gate_state == Character.GateState.REVIEW
        v1 = character.version
        assert v1 == 2

        request_character_changes(user, character, "make the narrator friendlier")
        character.refresh_from_db()
        assert character.gate_state == Character.GateState.REVISION_REQUESTED

        services.generate_characters(user, project)
        character.refresh_from_db()
        assert character.gate_state == Character.GateState.REVIEW
        assert character.version == v1 + 1
        assert len(character.characters) == 2
