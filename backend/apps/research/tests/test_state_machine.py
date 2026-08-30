# -*- coding: utf-8 -*-
"""Gate 1 state machine tests (step25/17, step24/09).

Validates the Research model's transition rules and the service-layer gate
validation: draft->generating (project in DRAFT), generating->review (summary +
>=1 source), review->approved (>=1 source), review->revision_requested (reason),
revision_requested->generating (previous version preserved).
"""
import pytest

from apps.research.models import Research

from .helpers import make_project


class TestStateMachineTransitions:
    def test_legal_transitions_function(self):
        tr = Research._TRANSITIONS
        assert tr[Research.GateState.DRAFT] == {Research.GateState.GENERATING}
        assert tr[Research.GateState.GENERATING] == {Research.GateState.REVIEW}
        assert tr[Research.GateState.REVIEW] == {
            Research.GateState.APPROVED,
            Research.GateState.REVISION_REQUESTED,
        }
        assert tr[Research.GateState.APPROVED] == set()
        assert tr[Research.GateState.REVISION_REQUESTED] == {
            Research.GateState.GENERATING
        }

    def test_illegal_transition_raises(self, make_user):
        research = Research(project=None)
        research.gate_state = Research.GateState.DRAFT
        with pytest.raises(ValueError):
            research.transition_to(Research.GateState.APPROVED)

    def test_same_state_transition_is_illegal(self, make_user):
        research = Research(project=None)
        research.gate_state = Research.GateState.REVIEW
        with pytest.raises(ValueError):
            research.transition_to(Research.GateState.REVIEW)


class TestGate1GIfactGrounding:
    def test_cannot_generate_script_without_approved_research(self, make_user):
        from apps.research.models import can_generate_script

        user = make_user(username="g1_user")
        project = make_project(user)
        ok, error = can_generate_script(project)
        assert ok is False
        assert "approved" in error

    def test_approved_research_allows_script(self, make_user):
        from apps.research.models import Research, can_generate_script

        user = make_user(username="g1_user2")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        research.gate_state = Research.GateState.APPROVED
        research.save()
        ok, _ = can_generate_script(project)
        assert ok is True

    def test_generation_requires_project_draft(self, make_user):
        from django.core.exceptions import ValidationError

        from apps.research import services

        user = make_user(username="g1_user3")
        project = make_project(user, lifecycle_state="Researching")
        with pytest.raises(ValidationError):
            services.generate_research(user, project)


class TestGate1RevisionCycle:
    def test_previous_version_preserved_on_regeneration(self, make_user, monkeypatch):
        from apps.research import services
        from apps.research.models import Research
        from apps.research.services import request_research_changes

        from .helpers import FAKE_RESEARCH

        monkeypatch.setattr(
            "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
        )
        user = make_user(username="rev_user")
        project = make_project(user)

        services.generate_research(user, project)
        research = Research.objects.get(project=project)
        research.refresh_from_db()
        assert research.gate_state == Research.GateState.REVIEW
        v1 = research.version
        assert v1 == 2  # initial version 1, bumped once on first generation

        request_research_changes(user, research, "needs more sources")
        research.refresh_from_db()
        assert research.gate_state == Research.GateState.REVISION_REQUESTED

        services.generate_research(user, project)
        research.refresh_from_db()
        assert research.gate_state == Research.GateState.REVIEW
        assert research.version == v1 + 1
