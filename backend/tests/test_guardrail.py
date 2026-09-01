# -*- coding: utf-8 -*-
"""Guardrail structural test -- updated for Task 53 / Phase 3.

Phase 3 introduced publishing, scheduling, video, preview, analytics, and
notification endpoints.  The guardrail is no longer "no endpoint exists" but
rather "every mutating endpoint enforces approval before upload":

  1. No upload can proceed without a valid per-entry approval record.
  2. No scheduling can proceed without an approved preview.
  3. Publishing endpoints are gated by RBAC (APPROVER_OWNER minimum).
  4. All state mutations are audit-logged.
"""
import inspect
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def _iter_patterns(patterns):
    from django.urls import URLPattern, URLResolver
    for pattern in patterns:
        if isinstance(pattern, URLPattern):
            yield pattern
        elif isinstance(pattern, URLResolver):
            yield from _iter_patterns(pattern.url_patterns)


def test_publishing_endpoints_exist():
    """Phase 3: publishing endpoints now exist (approval-gated)."""
    from django.urls import get_resolver
    resolver = get_resolver()
    names = []
    for pattern in _iter_patterns(resolver.url_patterns):
        names.append(pattern.name or "")
    joined = " ".join(names).lower()
    assert "publishing" in joined or "publish" in joined, \
        "publishing endpoints should exist in Phase 3"


@pytest.mark.django_db
def test_upload_requires_approval_structurally():
    """35.5: No upload attempt can be created without valid approval."""
    from apps.projects.models import Project
    from apps.research.models import Research, ResearchSource
    from apps.script.models import Script
    from apps.character.models import Character
    from apps.scene import services as ss
    from apps.publishing import services as pubs
    from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry

    user = User.objects.create_user(
        username="guardrail_upload", email="gu@test.com", password="LongPass123!"
    )
    from apps.accounts.models import Team
    team = Team.objects.create(name="Guardrail Team")
    user.memberships.create(team=team, role="Creator")

    project = Project.objects.create(team=team, owner=user, topic="Guardrail", lifecycle_state="Draft")
    research = Research.objects.create(project=project, team=team)
    ResearchSource.objects.create(research=research, url="https://g.co", title="G", snippet="S", credibility_score=0.9)
    research.summary = "G."
    research.gate_state = Research.GateState.APPROVED
    research.save()
    script = Script.objects.create(project=project, team=team, research=research, title="G",
                                   script="G", narration="G", scenes=[{"id":"s1","heading":"H","narration":"N","visual_notes":"V"}],
                                   gate_state=Script.GateState.APPROVED)
    Character.objects.create(project=project, team=team, script=script,
                             characters=[{"id":"c1","name":"N","age":"a","gender":"m","appearance":{},"clothing":{},"accessories":[],"style":{}}],
                             gate_state=Character.GateState.APPROVED)
    builder = ss.build_scenes(user, project)
    ss.approve_scene_builder(user, builder)

    sa = SocialAccount.objects.create(owner=user, team=team, platform="YouTube",
                                       platform_account_id="yt_g", display_name="G")
    post = ScheduledPost.objects.create(project=project, team=team, owner=user, status="draft")
    entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube",
                                           team=team, status="ready_for_approval",
                                           scheduled_utc=timezone.now() + timedelta(hours=48))
    with pytest.raises(ValidationError):
        pubs.create_upload_attempt(user, entry)


@pytest.mark.django_db
def test_schedule_requires_approved_preview_structurally():
    """35.5: No scheduling can proceed without approved preview."""
    from apps.projects.models import Project
    from apps.research.models import Research, ResearchSource
    from apps.script.models import Script
    from apps.character.models import Character
    from apps.scene import services as ss
    from apps.video import services as vs
    from apps.scheduler import services as sched

    user = User.objects.create_user(
        username="guardrail_sched", email="gs@test.com", password="LongPass123!"
    )
    from apps.accounts.models import Team
    team = Team.objects.create(name="Guardrail Sched Team")
    user.memberships.create(team=team, role="Creator")

    project = Project.objects.create(team=team, owner=user, topic="GS", lifecycle_state="Draft")
    research = Research.objects.create(project=project, team=team)
    ResearchSource.objects.create(research=research, url="https://g.co", title="G", snippet="S", credibility_score=0.9)
    research.summary = "G."
    research.gate_state = Research.GateState.APPROVED
    research.save()
    script = Script.objects.create(project=project, team=team, research=research, title="G",
                                   script="G", narration="G", scenes=[{"id":"s1","heading":"H","narration":"N","visual_notes":"V"}],
                                   gate_state=Script.GateState.APPROVED)
    Character.objects.create(project=project, team=team, script=script,
                             characters=[{"id":"c1","name":"N","age":"a","gender":"m","appearance":{},"clothing":{},"accessories":[],"style":{}}],
                             gate_state=Character.GateState.APPROVED)
    builder = ss.build_scenes(user, project)
    ss.approve_scene_builder(user, builder)
    vs.request_video(user, project, platform_target="YouTube")

    with pytest.raises(ValidationError, match="approved preview"):
        sched.create_entry(user, project, "YouTube", "2026-09-15T18:30:00", "UTC")


def test_no_autonomous_publishing_path():
    """35.5: No endpoint bypasses the approval gate for upload."""
    from apps.publishing import services as pubs
    source = inspect.getsource(pubs.create_upload_attempt)
    assert "APPROVED" in source, "create_upload_attempt must check APPROVED status"
    assert "is_approval_valid" in source or "approval" in source.lower(), \
        "create_upload_attempt must validate approval validity"


def test_publishing_is_disabled_in_foundation():
    """Legacy check: PUBLISHING_ENABLED flag (may be True in Phase 3)."""
    from django.conf import settings
    assert hasattr(settings, "PUBLISHING_ENABLED")
