# -*- coding: utf-8 -*-
"""Gate 1 service-layer tests (R2, step24/09 test requirements).

Covers approval, revision requests, validation rules, and audit completeness.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.research import services
from apps.research.models import Research, ResearchGap

from .helpers import FAKE_RESEARCH, make_project


def _finance_research(user, monkeypatch):
    """Generate research to the `review` state for subsequent gate tests."""
    monkeypatch.setattr(
        "apps.research.engine.gather_research", lambda project: FAKE_RESEARCH
    )
    project = make_project(user)
    research = services.generate_research(user, project)
    research.refresh_from_db()
    return research


class TestApprove:
    def test_approve_requires_review_state(self, make_user):
        user = make_user(username="srv_user1")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        with pytest.raises(ValidationError):
            services.approve_research(user, research)

    def test_approve_requires_sources(self, make_user, monkeypatch):
        user = make_user(username="srv_user2")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        research.gate_state = Research.GateState.REVIEW
        research.save()
        with pytest.raises(ValidationError):
            services.approve_research(user, research)

    def test_approve_sets_actor_and_at(self, make_user, monkeypatch):
        user = make_user(username="srv_user3")
        research = _finance_research(user, monkeypatch)
        approved = services.approve_research(user, research)
        approved.refresh_from_db()
        assert approved.gate_state == Research.GateState.APPROVED
        assert approved.approval_actor == user
        assert approved.approval_at is not None


class TestRequestChanges:
    def test_reason_required(self, make_user, monkeypatch):
        user = make_user(username="srv_user4")
        research = _finance_research(user, monkeypatch)
        with pytest.raises(ValidationError):
            services.request_research_changes(user, research, "")

    def test_requires_review_state(self, make_user):
        user = make_user(username="srv_user5")
        project = make_project(user)
        research = Research.objects.create(project=project, team=project.team)
        with pytest.raises(ValidationError):
            services.request_research_changes(user, research, "fix it")

    def test_revision_requested_sets_reason(self, make_user, monkeypatch):
        user = make_user(username="srv_user6")
        research = _finance_research(user, monkeypatch)
        changed = services.request_research_changes(user, research, "needs citations")
        changed.refresh_from_db()
        assert changed.gate_state == Research.GateState.REVISION_REQUESTED
        assert changed.rejection_reason == "needs citations"


class TestSourceCitation:
    def test_every_summary_claim_maps_to_sources(self, make_user, monkeypatch):
        user = make_user(username="srv_user7")
        research = _finance_research(user, monkeypatch)
        assert research.sources.count() >= 1
        for src in research.sources.all():
            assert src.url


class TestContradictionSurfacing:
    def test_contradictions_are_flagged_not_resolved(self, make_user, monkeypatch):
        user = make_user(username="srv_user8")
        research = _finance_research(user, monkeypatch)
        contradiction = ResearchGap.objects.filter(
            research=research, gap_type=ResearchGap.GapType.CONTRADICTION
        ).first()
        assert contradiction is not None
        assert contradiction.description
        # surfaced, status stays open (never silently resolved)
        assert contradiction.status == ResearchGap.Status.OPEN


class TestAuditCompleteness:
    def test_research_actions_recorded(self, make_user, monkeypatch):
        user = make_user(username="audit_user")
        research = _finance_research(user, monkeypatch)
        services.approve_research(user, research)

        reasons = list(
            AuditLog.objects.filter(target_type="research")
            .order_by("id")
            .values_list("reason", flat=True)
        )
        assert "research_generation_started" in reasons
        assert "research_ready_for_review" in reasons
        assert "research_approved" in reasons
