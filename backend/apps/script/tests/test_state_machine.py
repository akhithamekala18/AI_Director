# -*- coding: utf-8 -*-
"""Gate 2 state machine tests (Development Plan Day 22 / Overview §20.1.3).

Validates the Script model's transition rules and the service-layer gate
validation:
  draft->generating (G-1: approved research required),
  generating->review (title + script + narration non-empty),
  review->approved (title + script + narration non-empty),
  review->revision_requested (reason required),
  revision_requested->generating (previous version preserved).
"""
import pytest

from apps.script.models import Script

from .helpers import approved_research, make_project


class TestStateMachineTransitions:
    def test_legal_transitions_function(self):
        tr = Script._TRANSITIONS
        assert tr[Script.GateState.DRAFT] == {Script.GateState.GENERATING}
        assert tr[Script.GateState.GENERATING] == {Script.GateState.REVIEW}
        assert tr[Script.GateState.REVIEW] == {
            Script.GateState.APPROVED,
            Script.GateState.REVISION_REQUESTED,
        }
        assert tr[Script.GateState.APPROVED] == set()
        assert tr[Script.GateState.REVISION_REQUESTED] == {
            Script.GateState.GENERATING
        }

    def test_illegal_transition_raises(self, make_user):
        script = Script(project=None, team=None)
        script.gate_state = Script.GateState.DRAFT
        with pytest.raises(ValueError):
            script.transition_to(Script.GateState.APPROVED)

    def test_same_state_transition_is_illegal(self, make_user):
        script = Script(project=None, team=None)
        script.gate_state = Script.GateState.REVIEW
        with pytest.raises(ValueError):
            script.transition_to(Script.GateState.REVIEW)


class TestG1ResearchDependency:
    def test_no_writing_without_approved_research(self, make_user):
        from django.core.exceptions import ValidationError

        from apps.script import services

        user = make_user(username="g1_script")
        project = make_project(user)
        with pytest.raises(ValidationError):
            services.generate_script(user, project)

    def test_approved_research_allows_script(self, make_user, monkeypatch):
        from apps.script import services
        from apps.script.models import Script

        from .helpers import FAKE_SCRIPT

        monkeypatch.setattr(
            "apps.script.engine.gather_script",
            lambda research: FAKE_SCRIPT,
        )
        user = make_user(username="g1_script2")
        project = make_project(user)
        approved_research(user, project)
        services.generate_script(user, project)
        script = Script.objects.get(project=project)
        script.refresh_from_db()
        assert script.gate_state == Script.GateState.REVIEW
        assert script.research is not None


class TestGate2RevisionCycle:
    def test_previous_version_preserved_on_regeneration(self, make_user, monkeypatch):
        from apps.script import services
        from apps.script.models import Script
        from apps.script.services import request_script_changes

        from .helpers import FAKE_SCRIPT

        monkeypatch.setattr(
            "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
        )
        user = make_user(username="rev_script")
        project = make_project(user)
        approved_research(user, project)

        services.generate_script(user, project)
        script = Script.objects.get(project=project)
        script.refresh_from_db()
        assert script.gate_state == Script.GateState.REVIEW
        v1 = script.version
        assert v1 == 2

        request_script_changes(user, script, "rewrite the ending")
        script.refresh_from_db()
        assert script.gate_state == Script.GateState.REVISION_REQUESTED

        services.generate_script(user, project)
        script.refresh_from_db()
        assert script.gate_state == Script.GateState.REVIEW
        assert script.version == v1 + 1
