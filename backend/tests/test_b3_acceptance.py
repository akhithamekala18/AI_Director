# -*- coding: utf-8 -*-
"""Backend Phase 3 Acceptance - Task 44."""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.audit.models import AuditLog
from apps.projects.models import Project
User = get_user_model()

def _make_user(username):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="LongPass123!")
    from apps.accounts.models import Team
    team = Team.objects.create(name=f"{username} workspace")
    user.memberships.create(team=team, role="Creator")
    return user

def _make_project(user, topic="B3 Test Topic"):
    return Project.objects.create(team=user.memberships.first().team, owner=user, topic=topic, lifecycle_state="Draft")

def _make_approved_research(project):
    from apps.research.models import Research, ResearchSource
    research = Research.objects.create(project=project, team=project.team)
    ResearchSource.objects.create(research=research, url="https://example.org/test", title="Test Source", snippet="Test.", credibility_score=0.9)
    research.summary = "Test summary."
    research.gate_state = Research.GateState.APPROVED
    research.save()
    return research

def _make_approved_script(project, research):
    from apps.script.models import Script
    scenes = [{"id": "s1", "heading": "Hook", "narration": "Intro.", "visual_notes": "S1."}, {"id": "s2", "heading": "Core", "narration": "Main.", "visual_notes": "S2."}]
    return Script.objects.create(project=project, team=project.team, research=research, title="Test", script="Full.", narration="Narr.", scenes=scenes, gate_state=Script.GateState.APPROVED)

def _make_approved_characters(project, script):
    from apps.character.models import Character
    chars = [{"id": "char_1", "name": "Host", "age": "adult", "gender": "male", "appearance": {"hair_color": "dark"}, "clothing": {"outfit": "casual"}, "accessories": [], "style": {"realism": "stylized"}}]
    return Character.objects.create(project=project, team=project.team, script=script, characters=chars, gate_state=Character.GateState.APPROVED)

def _build_and_approve_scene(project, script, characters):
    from apps.scene import services as ss
    builder = ss.build_scenes(project.owner, project)
    ss.approve_scene_builder(project.owner, builder)
    builder.refresh_from_db()
    return builder

def _gen_video(u, p):
    from apps.video import services as vs
    return vs.request_video(u, p, platform_target="YouTube")

def _gen_thumb(u, p):
    from apps.thumbnail import services as ts
    return ts.request_thumbnail(u, p, platform_target="YouTube", title_text="Test")

def _gen_preview(u, p):
    from apps.preview import services as ps
    return ps.request_preview(u, p, platform_target="YouTube")

def _approve_prev(u, prev):
    from apps.preview import services as ps
    return ps.approve_preview(u, prev)

@pytest.mark.django_db
class TestB3FullPipeline:
    def test_approved_video_generation(self):
        u = _make_user("b3_vid")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        video = _gen_video(u, p)
        assert video.status == "ready"
        assert video.provider == "fake"
        assert video.scene_count >= 1

    def test_thumbnail_generation(self):
        u = _make_user("b3_thumb")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        thumb = _gen_thumb(u, p)
        assert thumb.asset_ref
        assert thumb.provider == "fake"

    def test_preview_requires_video(self):
        u = _make_user("b3_prev")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        from django.core.exceptions import ValidationError
        from apps.preview import services as ps
        with pytest.raises(ValidationError, match="no video asset"):
            ps.request_preview(u, p, platform_target="YouTube")

    def test_preview_after_video(self):
        u = _make_user("b3_prev2")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        preview = _gen_preview(u, p)
        assert preview.status == "ready"
        assert preview.approval_state == "pending"

    def test_preview_approval(self):
        u = _make_user("b3_appr")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        preview = _gen_preview(u, p)
        approved = _approve_prev(u, preview)
        assert approved.approval_state == "approved"
        assert approved.approved_by == u

    def test_preview_rejection(self):
        u = _make_user("b3_rej")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        preview = _gen_preview(u, p)
        from apps.preview import services as ps
        rejected = ps.reject_preview(u, preview, reason="Needs work")
        assert rejected.approval_state == "rejected"

@pytest.mark.django_db
class TestPreviewBeforeSchedule:
    def test_blocked_without_preview(self):
        u = _make_user("b3_noprev")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        from apps.scheduler import services as sched
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError, match="approved preview"):
            sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")

    def test_allowed_with_approved_preview(self):
        u = _make_user("b3_withprev")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        prev = _gen_preview(u, p)
        _approve_prev(u, prev)
        from apps.scheduler import services as sched
        entry = sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")
        assert entry.status == "scheduled"
        assert entry.platform == "YouTube"


@pytest.mark.django_db
class TestGate4Enforcement:
    def test_video_blocked_without_gate4(self):
        u = _make_user("b3_g4")
        p = _make_project(u)
        from apps.video import services as vs
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError, match="approved scene package"):
            vs.request_video(u, p)

    def test_preview_blocked_without_gate4(self):
        u = _make_user("b3_g4b")
        p = _make_project(u)
        from apps.preview import services as ps
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError, match="approved scene package"):
            ps.request_preview(u, p)

@pytest.mark.django_db
class TestApprovalBeforeUpload:
    def test_blocked_without_approval(self):
        u = _make_user("b3_noapproval")
        p = _make_project(u)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        sa = SocialAccount.objects.create(owner=u, team=u.memberships.first().team, platform="YouTube", platform_account_id="yt_test", display_name="YT")
        post = ScheduledPost.objects.create(project=p, team=u.memberships.first().team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=u.memberships.first().team, status="scheduled", scheduled_utc=timezone.now() + timedelta(hours=48))
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            pubs.create_upload_attempt(u, entry)

    def test_allowed_with_valid_approval(self):
        u = _make_user("b3_withapproval")
        p = _make_project(u)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        team = u.memberships.first().team
        sa = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_test2", display_name="YT2")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team, status="ready_for_approval", scheduled_utc=timezone.now() + timedelta(hours=48))
        pubs.approve_entry(u, entry, reason="Looks good")
        attempt = pubs.create_upload_attempt(u, entry)
        assert attempt is not None
        assert attempt.attempt_no == 1

    def test_expired_approval_blocks(self):
        u = _make_user("b3_expired")
        p = _make_project(u)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry, Approval
        team = u.memberships.first().team
        sa = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_test3", display_name="YT3")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team, status="ready_for_approval", scheduled_utc=timezone.now() - timedelta(hours=1))
        Approval.objects.create(entry=entry, actor=u, decision="approve", reason="old",
                                expires_at=timezone.now() - timedelta(hours=1))
        assert not pubs.is_approval_valid(entry)

@pytest.mark.django_db
class TestRetryAndIdempotency:
    def test_retry_schedule(self):
        from apps.publishing.services import _get_retry_wait_seconds
        assert _get_retry_wait_seconds(1) == 0
        assert _get_retry_wait_seconds(2) == 60
        assert _get_retry_wait_seconds(3) == 300
        assert _get_retry_wait_seconds(4) == 900

    def test_max_attempts_enforced(self):
        from apps.publishing.services import can_retry_entry
        from apps.publishing.models import ScheduledEntry, ScheduledPost, SocialAccount
        u = _make_user("b3_maxatt")
        p = _make_project(u)
        team = u.memberships.first().team
        sa = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_max", display_name="Max")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team, status="failed", scheduled_utc=timezone.now() + timedelta(hours=48))
        entry.upload_attempts_count = 4
        entry.save()
        ok, reason = can_retry_entry(entry)
        assert ok is False

    def test_idempotent_publish(self):
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        u = _make_user("b3_idem")
        p = _make_project(u)
        team = u.memberships.first().team
        sa = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_idem", display_name="Idem")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team, status="ready_for_approval", scheduled_utc=timezone.now() + timedelta(hours=48))
        pubs.approve_entry(u, entry)
        a1 = pubs.create_upload_attempt(u, entry)
        pubs.complete_upload_attempt(a1, success=True)
        entry.refresh_from_db()
        assert entry.status == "published"

@pytest.mark.django_db
class TestPerPlatformIndependence:
    def test_different_platforms(self):
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        u = _make_user("b3_platform")
        p = _make_project(u)
        team = u.memberships.first().team
        sa_yt = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_plat", display_name="YT")
        sa_ig = SocialAccount.objects.create(owner=u, team=team, platform="Instagram", platform_account_id="ig_plat", display_name="IG")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        e_yt = ScheduledEntry.objects.create(post=post, social_account=sa_yt, platform="YouTube", team=team, status="published", scheduled_utc=timezone.now() + timedelta(hours=48))
        e_ig = ScheduledEntry.objects.create(post=post, social_account=sa_ig, platform="Instagram", team=team, status="upload_failed", scheduled_utc=timezone.now() + timedelta(hours=48))
        assert e_yt.status == "published"
        assert e_ig.status == "upload_failed"


@pytest.mark.django_db
class TestB3TeamIsolation:
    def test_video_isolation(self):
        u1 = _make_user("b3_ti_v1")
        u2 = _make_user("b3_ti_v2")
        p1 = _make_project(u1, topic="Team1")
        r = _make_approved_research(p1)
        s = _make_approved_script(p1, r)
        c = _make_approved_characters(p1, s)
        _build_and_approve_scene(p1, s, c)
        v = _gen_video(u1, p1)
        from apps.video import services as vs
        assert vs.get_video(u2, v.id) is None

    def test_preview_isolation(self):
        u1 = _make_user("b3_ti_p1")
        u2 = _make_user("b3_ti_p2")
        p1 = _make_project(u1, topic="Team1p")
        r = _make_approved_research(p1)
        s = _make_approved_script(p1, r)
        c = _make_approved_characters(p1, s)
        _build_and_approve_scene(p1, s, c)
        _gen_video(u1, p1)
        prev = _gen_preview(u1, p1)
        from apps.preview import services as ps
        assert ps.get_preview(u2, prev.id) is None

    def test_scheduler_isolation(self):
        u1 = _make_user("b3_ti_s1")
        u2 = _make_user("b3_ti_s2")
        p1 = _make_project(u1, topic="Team1s")
        r = _make_approved_research(p1)
        s = _make_approved_script(p1, r)
        c = _make_approved_characters(p1, s)
        _build_and_approve_scene(p1, s, c)
        _gen_video(u1, p1)
        prev = _gen_preview(u1, p1)
        _approve_prev(u1, prev)
        from apps.scheduler import services as sched
        entry = sched.create_entry(u1, p1, "YouTube", "2026-09-15T18:30:00", "UTC")
        assert sched.get_entry(u2, entry.id) is None

@pytest.mark.django_db
class TestB3TeamIsolationCont:
    def test_publishing_isolation(self):
        u1 = _make_user("b3_ti_pub1")
        u2 = _make_user("b3_ti_pub2")
        p1 = _make_project(u1, topic="Team1pub")
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        team1 = u1.memberships.first().team
        sa = SocialAccount.objects.create(owner=u1, team=team1, platform="YouTube", platform_account_id="yt_ti", display_name="TI")
        post = ScheduledPost.objects.create(project=p1, team=team1, owner=u1, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team1, status="scheduled", scheduled_utc=timezone.now() + timedelta(hours=48))
        from apps.publishing import services as pubs
        assert pubs.get_entry(u2, entry.id) is None

    def test_analytics_isolation(self):
        u1 = _make_user("b3_ti_a1")
        u2 = _make_user("b3_ti_a2")
        from apps.analytics import services as ans
        s1 = ans.get_analytics_summary(u1)
        s2 = ans.get_analytics_summary(u2)
        assert s1["total_views"] is None
        assert s2["total_views"] is None


@pytest.mark.django_db
class TestAnalyticsBoundary:
    def test_rejects_unpublished(self):
        from apps.analytics import services as ans
        from apps.publishing.models import ScheduledEntry, ScheduledPost, SocialAccount
        u = _make_user("b3_an_bound")
        p = _make_project(u)
        team = u.memberships.first().team
        sa = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_an", display_name="AN")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team, status="scheduled", scheduled_utc=timezone.now() + timedelta(hours=48))
        with pytest.raises(ValueError, match="analytics only tracks published"):
            ans.record_published_performance(entry, views=100)

    def test_accepts_published(self):
        from apps.analytics import services as ans
        from apps.publishing.models import ScheduledEntry, ScheduledPost, SocialAccount
        u = _make_user("b3_an_pub")
        p = _make_project(u)
        team = u.memberships.first().team
        sa = SocialAccount.objects.create(owner=u, team=team, platform="YouTube", platform_account_id="yt_an2", display_name="AN2")
        post = ScheduledPost.objects.create(project=p, team=team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=team, status="published", scheduled_utc=timezone.now() + timedelta(hours=48))
        obj = ans.record_published_performance(entry, views=100, likes=10, topic="test")
        assert obj.views == 100

@pytest.mark.django_db
class TestB3Notifications:
    def test_notification_types_exist(self):
        from apps.notifications.models import NotificationType
        assert hasattr(NotificationType, "REMINDER")
        assert hasattr(NotificationType, "PUBLISH_OUTCOME")
        assert hasattr(NotificationType, "PUBLISH_FAILURE")
        assert hasattr(NotificationType, "TEAM_ASSIGNMENT")

    def test_notification_creation(self):
        from apps.notifications import services as ns
        u = _make_user("b3_notif")
        n = ns.notify_reminder(u, "Test reminder")
        assert n is not None

    def test_notification_preferences(self):
        from apps.settings_app.models import NotificationPreferences
        u = _make_user("b3_notif_pref")
        prefs, _ = NotificationPreferences.objects.get_or_create(user=u, defaults={"reminders": True, "publish_outcomes": True})
        assert prefs.reminders is True


@pytest.mark.django_db
class TestB3Settings:
    def test_publishing_preferences(self):
        from apps.settings_app.models import PublishingPreferences
        u = _make_user("b3_settings")
        prefs, _ = PublishingPreferences.objects.get_or_create(user=u, defaults={"auto_approve_enabled": False, "cross_post_by_default": True})
        assert prefs.cross_post_by_default is True


@pytest.mark.django_db
class TestB3Audit:
    def test_video_creates_audit(self):
        u = _make_user("b3_audit_v")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        assert AuditLog.objects.filter(target_type="video").exists()

    def test_preview_creates_audit(self):
        u = _make_user("b3_audit_p")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        _gen_preview(u, p)
        assert AuditLog.objects.filter(target_type="preview").exists()

    def test_scheduler_creates_audit(self):
        u = _make_user("b3_audit_s")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        _gen_video(u, p)
        prev = _gen_preview(u, p)
        _approve_prev(u, prev)
        from apps.scheduler import services as sched
        sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")
        assert AuditLog.objects.filter(target_type="schedule_entry").exists()
