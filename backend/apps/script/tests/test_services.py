# -*- coding: utf-8 -*-
"""Gate 2 service-layer tests (R2, Development Plan Day 22).

Covers approval, revision requests, validation rules, and audit completeness
for the Script artifact and its Gate 2 state machine.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.script import services
from apps.script.models import Script

from .helpers import FAKE_SCRIPT, approved_research, make_project


def _finance_script(user, monkeypatch):
    """Generate a script to the `review` state for subsequent gate tests."""
    monkeypatch.setattr(
        "apps.script.engine.gather_script", lambda research: FAKE_SCRIPT
    )
    project = make_project(user)
    approved_research(user, project)
    script = services.generate_script(user, project)
    script.refresh_from_db()
    return script


class TestApprove:
    def test_approve_requires_review_state(self, make_user):
        user = make_user(username="srv_script1")
        project = make_project(user)
        approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team)
        with pytest.raises(ValidationError):
            services.approve_script(user, script)

    def test_approve_requires_generated_script(self, make_user):
        user = make_user(username="srv_script2")
        project = make_project(user)
        approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team)
        script.gate_state = Script.GateState.REVIEW
        script.save()
        with pytest.raises(ValidationError):
            services.approve_script(user, script)

    def test_approve_sets_actor_and_at(self, make_user, monkeypatch):
        user = make_user(username="srv_script3")
        script = _finance_script(user, monkeypatch)
        approved = services.approve_script(user, script)
        approved.refresh_from_db()
        assert approved.gate_state == Script.GateState.APPROVED
        assert approved.approval_actor == user
        assert approved.approval_at is not None


class TestRequestChanges:
    def test_reason_required(self, make_user, monkeypatch):
        user = make_user(username="srv_script4")
        script = _finance_script(user, monkeypatch)
        with pytest.raises(ValidationError):
            services.request_script_changes(user, script, "")

    def test_requires_review_state(self, make_user):
        user = make_user(username="srv_script5")
        project = make_project(user)
        approved_research(user, project)
        script = Script.objects.create(project=project, team=project.team)
        with pytest.raises(ValidationError):
            services.request_script_changes(user, script, "fix it")

    def test_revision_requested_sets_reason(self, make_user, monkeypatch):
        user = make_user(username="srv_script6")
        script = _finance_script(user, monkeypatch)
        changed = services.request_script_changes(
            user, script, "rewrite the ending"
        )
        changed.refresh_from_db()
        assert changed.gate_state == Script.GateState.REVISION_REQUESTED
        assert changed.rejection_reason == "rewrite the ending"


class TestAuditCompleteness:
    def test_script_actions_recorded(self, make_user, monkeypatch):
        user = make_user(username="audit_script")
        script = _finance_script(user, monkeypatch)
        services.approve_script(user, script)

        reasons = list(
            AuditLog.objects.filter(target_type="script")
            .order_by("id")
            .values_list("reason", flat=True)
        )
        assert "script_generation_started" in reasons
        assert "script_ready_for_review" in reasons
        assert "script_approved" in reasons
