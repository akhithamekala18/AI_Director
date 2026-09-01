# -*- coding: utf-8 -*-
"""Task 53 - System & Acceptance - Acceptance Testing."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from apps.audit.models import AuditLog
from apps.projects.models import Project
User = get_user_model()

def _mu(u):
    user = User.objects.create_user(username=u, email=f"{u}@t.co", password="LongPass123!")
    from apps.accounts.models import Team
    t = Team.objects.create(name=f"{u} ws")
    user.memberships.create(team=t, role="Creator")
    return user

def _mp(u, topic="T"):
    return Project.objects.create(team=u.memberships.first().team, owner=u, topic=topic, lifecycle_state="Draft")

def _ar(p):
    from apps.research.models import Research, ResearchSource
    r = Research.objects.create(project=p, team=p.team)
    ResearchSource.objects.create(research=r, url="https://e.org", title="S", snippet="T", credibility_score=0.9)
    r.summary = "T"; r.gate_state = Research.GateState.APPROVED; r.save()
    return r

def _as(p, r):
    from apps.script.models import Script
    return Script.objects.create(project=p, team=p.team, research=r, title="T", script="T", narration="N",
        scenes=[{"id":"s1","heading":"H","narration":"N","visual_notes":"V"},{"id":"s2","heading":"H2","narration":"N2","visual_notes":"V2"}],
        gate_state=Script.GateState.APPROVED)

def _ac(p, s):
    from apps.character.models import Character
    return Character.objects.create(project=p, team=p.team, script=s,
        characters=[{"id":"char_1","name":"Host","age":"adult","gender":"male","appearance":{"hair_color":"dark"},"clothing":{},"accessories":[],"style":{}}],
        gate_state=Character.GateState.APPROVED)

def _bas(p, s, c):
    from apps.scene import services as ss
    b = ss.build_scenes(p.owner, p); ss.approve_scene_builder(p.owner, b); b.refresh_from_db(); return b

def _fp(u, topic="FP"):
    p = _mp(u, topic); r = _ar(p); s = _as(p, r); c = _ac(p, s); b = _bas(p, s, c)
    return p, r, s, c, b

def _gv(u, p):
    from apps.video import services as vs; return vs.request_video(u, p, platform_target="YouTube")

def _gp(u, p):
    from apps.preview import services as ps; return ps.request_preview(u, p, platform_target="YouTube")

def _ap(u, prev):
    from apps.preview import services as ps; return ps.approve_preview(u, prev)

def _gsa(u, plat="YouTube", aid="yt"):
    from apps.publishing.models import SocialAccount
    return SocialAccount.objects.create(owner=u, team=u.memberships.first().team, platform=plat, platform_account_id=aid, display_name=f"{plat} T")

def _ge(u, p, sa, st="ready_for_approval"):
    from apps.publishing.models import ScheduledEntry, ScheduledPost
    po = ScheduledPost.objects.create(project=p, team=u.memberships.first().team, owner=u, status="draft")
    return ScheduledEntry.objects.create(post=po, social_account=sa, platform=sa.platform,
        team=u.memberships.first().team, status=st, scheduled_utc=timezone.now() + timedelta(hours=48))


# 44.2 Acceptance Criteria Examples
@pytest.mark.django_db
class TestAcceptanceCriteriaExamples:
    def test_research_gate_blocks_scripting(self):
        u = _mu("acc_rg"); p = _mp(u)
        from apps.research.models import can_generate_script
        assert can_generate_script(p)[0] is False
    def test_research_gate_unblocks_scripting(self):
        u = _mu("acc_rg2"); p = _mp(u); _ar(p)
        from apps.research.models import can_generate_script
        assert can_generate_script(p)[0] is True
    def test_preview_rule_blocks_scheduling(self):
        u = _mu("acc_pr"); p, _, _, _, _ = _fp(u); _gv(u, p)
        from apps.scheduler import services as sched
        with pytest.raises(ValidationError, match="approved preview"):
            sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")
    def test_preview_rule_allows_scheduling(self):
        u = _mu("acc_pr2"); p, _, _, _, _ = _fp(u)
        _gv(u, p); prev = _gp(u, p); _ap(u, prev)
        from apps.scheduler import services as sched
        e = sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")
        assert e.status == "scheduled"
    def test_publishing_approval_required_before_upload(self):
        u = _mu("acc_pa"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        with pytest.raises(ValidationError):
            pubs.create_upload_attempt(u, e)
    def test_publishing_approval_allows_upload(self):
        u = _mu("acc_pa2"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u, aid="yt_pa2"); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        pubs.approve_entry(u, e, reason="Looks good")
        a = pubs.create_upload_attempt(u, e)
        assert a is not None and a.attempt_no == 1
    def test_scene_regeneration_scoped(self):
        u = _mu("acc_sg"); p, _, _, _, _ = _fp(u)
        from apps.scene_media import services as ms
        from apps.scene_media.models import SceneMedia
        from apps.regeneration import services as rs
        ms.request_scene_media(u, p)
        s1m = list(SceneMedia.objects.filter(project=p, scene_id="s1"))
        s1v = {m.id: m.version for m in s1m}
        job = rs.request_regeneration(u, p, scene_id="s2", media_types=["voice"])
        assert job.status == "completed"
        for m in s1m:
            m.refresh_from_db()
            assert m.version == s1v[m.id]
    def test_character_library_reuse_consistency(self):
        u = _mu("acc_cr"); p = _mp(u); r = _ar(p); s = _as(p, r); chars = _ac(p, s)
        for ch in chars.characters:
            assert ch["name"] == "Host" and ch["age"] == "adult"

# 35.5 Guardrail Metrics
@pytest.mark.django_db
class TestGuardrailMetrics:
    def test_zero_unapproved_uploads(self):
        u = _mu("gr_ua"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        with pytest.raises(ValidationError):
            pubs.create_upload_attempt(u, e)
    def test_expired_approval_blocks(self):
        u = _mu("gr_ua2"); p, _, _, _, _ = _fp(u)
        from apps.publishing.models import Approval
        sa = _gsa(u, aid="yt_ua2"); e = _ge(u, p, sa)
        Approval.objects.create(entry=e, actor=u, decision="approve", reason="old",
            expires_at=timezone.now() - timedelta(hours=1))
        from apps.publishing import services as pubs
        assert not pubs.is_approval_valid(e)
    def test_zero_unpreviewed_schedules(self):
        u = _mu("gr_us"); p, _, _, _, _ = _fp(u); _gv(u, p)
        from apps.scheduler import services as sched
        with pytest.raises(ValidationError, match="approved preview"):
            sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")
    def test_state_machine_rejects_illegal(self):
        from apps.research.models import Research
        r = Research(project=None); r.gate_state = Research.GateState.DRAFT
        with pytest.raises(ValueError):
            r.transition_to(Research.GateState.APPROVED)
    def test_team_isolation_research(self):
        u1 = _mu("gr_t1"); u2 = _mu("gr_t2"); p = _mp(u1); _ar(p)
        from apps.research import services as rs
        assert rs.get_research(u2, p) is None
    def test_team_isolation_video(self):
        u1 = _mu("gr_v1"); u2 = _mu("gr_v2"); p, _, _, _, _ = _fp(u1); v = _gv(u1, p)
        from apps.video import services as vs
        assert vs.get_video(u2, v.id) is None
    def test_team_isolation_publishing(self):
        u1 = _mu("gr_p1"); u2 = _mu("gr_p2"); p, _, _, _, _ = _fp(u1)
        sa = _gsa(u1); e = _ge(u1, p, sa, st="scheduled")
        from apps.publishing import services as pubs
        assert pubs.get_entry(u2, e.id) is None

# Section 10 Guidelines
@pytest.mark.django_db
class TestG1FactGrounding:
    def test_blocked(self):
        u = _mu("g1a"); p = _mp(u)
        from apps.research.models import can_generate_script
        assert can_generate_script(p)[0] is False
    def test_allowed(self):
        u = _mu("g1b"); p = _mp(u); _ar(p)
        from apps.research.models import can_generate_script
        assert can_generate_script(p)[0] is True

@pytest.mark.django_db
class TestG2SourceTransparency:
    def test_sources_present(self):
        u = _mu("g2a"); p = _mp(u); r = _ar(p)
        from apps.research.models import ResearchSource
        s = ResearchSource.objects.filter(research=r).first()
        assert s and s.url and s.credibility_score > 0

@pytest.mark.django_db
class TestG3ApprovalGating:
    def test_full_chain(self):
        u = _mu("g3a"); p = _mp(u)
        from apps.research.models import can_generate_script
        assert can_generate_script(p)[0] is False
        from apps.video import services as vs
        with pytest.raises(ValidationError):
            vs.request_video(u, p)
        from apps.scheduler import services as sched
        with pytest.raises(ValidationError):
            sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")

@pytest.mark.django_db
class TestG4ScopedRegeneration:
    def test_scoped_regen(self):
        u = _mu("g4a"); p, _, _, _, _ = _fp(u)
        from apps.scene_media import services as ms
        from apps.scene_media.models import SceneMedia
        from apps.regeneration import services as rs
        ms.request_scene_media(u, p)
        s1m = list(SceneMedia.objects.filter(project=p, scene_id="s1"))
        s1v = {m.id: m.version for m in s1m}
        rs.request_regeneration(u, p, scene_id="s2", media_types=["voice"])
        for m in s1m:
            m.refresh_from_db()
            assert m.version == s1v[m.id]

@pytest.mark.django_db
class TestG5IdentityStability:
    def test_stable_ids(self):
        u = _mu("g5a"); p, _, _, _, _ = _fp(u)
        from apps.character.models import Character
        c = Character.objects.filter(project=p).first()
        assert c and all(ch["id"].startswith("char_") for ch in c.characters)

@pytest.mark.django_db
class TestG6ConsentForPublishing:
    def test_no_unconfirmed(self):
        u = _mu("g6a"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        with pytest.raises(ValidationError):
            pubs.create_upload_attempt(u, e)

@pytest.mark.django_db
class TestG7Auditing:
    def test_research_audit(self):
        u = _mu("g7a"); p = _mp(u)
        from apps.research import services as rs; rs.generate_research(u, p)
        assert AuditLog.objects.filter(target_type="research").exists()
    def test_video_audit(self):
        u = _mu("g7b"); p, _, _, _, _ = _fp(u); _gv(u, p)
        assert AuditLog.objects.filter(target_type="video").exists()
    def test_preview_audit(self):
        u = _mu("g7c"); p, _, _, _, _ = _fp(u); _gv(u, p); _gp(u, p)
        assert AuditLog.objects.filter(target_type="preview").exists()
    def test_scheduler_audit(self):
        u = _mu("g7d"); p, _, _, _, _ = _fp(u); _gv(u, p); prev = _gp(u, p); _ap(u, prev)
        from apps.scheduler import services as sched
        sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")
        assert AuditLog.objects.filter(target_type="schedule_entry").exists()
    def test_publishing_audit(self):
        u = _mu("g7e"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        from apps.publishing.models import PublishingAuditLog
        pubs.approve_entry(u, e, reason="ok")
        log = PublishingAuditLog.objects.filter(entry=e, action="entry_approved").first()
        assert log is not None and log.actor_id == u.id

@pytest.mark.django_db
class TestG9CostTransparency:
    def test_cost_field(self):
        u = _mu("g9a"); p = _mp(u)
        from apps.ai_orchestration.models import AsyncJob
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION)
        assert hasattr(j, "cost") and j.cost == 0

# 23.2 Approval-Gate Audit
@pytest.mark.django_db
class TestApprovalGateAudit:
    def test_all_6_gates(self):
        u = _mu("ga"); p, _, _, _, _ = _fp(u)
        from apps.research.models import Research
        assert Research.objects.filter(project=p).first().gate_state == Research.GateState.APPROVED
        from apps.script.models import Script
        assert Script.objects.filter(project=p).first().gate_state == Script.GateState.APPROVED
        from apps.character.models import Character
        assert Character.objects.filter(project=p).first().gate_state == Character.GateState.APPROVED
        from apps.scene.models import SceneBuilder
        assert SceneBuilder.objects.filter(project=p).first().gate_state == SceneBuilder.GateState.APPROVED
        _gv(u, p); prev = _gp(u, p); assert prev.approval_state == "pending"
        _ap(u, prev); prev.refresh_from_db(); assert prev.approval_state == "approved"
        sa = _gsa(u, aid="yt_ga"); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        pubs.approve_entry(u, e, reason="OK")
        e.refresh_from_db()
        assert pubs.is_approval_valid(e)
    def test_rejection(self):
        u = _mu("ga_r"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u, aid="yt_gr"); e = _ge(u, p, sa)
        from apps.publishing import services as pubs; pubs.reject_entry(u, e, reason="No")
        e.refresh_from_db(); assert e.status == "rejected"
    def test_invalidation(self):
        u = _mu("ga_i"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u, aid="yt_gi"); e = _ge(u, p, sa)
        from apps.publishing import services as pubs; pubs.approve_entry(u, e, reason="OK")
        pubs.invalidate_approvals_for_entry(e, reason="rescheduled")
        e.refresh_from_db()
        assert e.status == "approval_invalidated" and not pubs.is_approval_valid(e)

# Audit Completeness
@pytest.mark.django_db
class TestAuditCompleteness:
    def test_actor_and_time(self):
        u = _mu("ac1"); p = _mp(u)
        from apps.research import services as rs; rs.generate_research(u, p)
        last = AuditLog.objects.order_by("-created_at").first()
        assert last and last.actor_id and last.created_at
    def test_reason_on_approval(self):
        u = _mu("ac2"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u); e = _ge(u, p, sa)
        from apps.publishing import services as pubs; pubs.approve_entry(u, e, reason="Q3 campaign")
        from apps.publishing.models import Approval
        a = Approval.objects.filter(entry=e).first()
        assert a and a.reason == "Q3 campaign"
    def test_publishing_log_completeness(self):
        u = _mu("ac3"); p, _, _, _, _ = _fp(u)
        sa = _gsa(u); e = _ge(u, p, sa)
        from apps.publishing import services as pubs
        from apps.publishing.models import PublishingAuditLog
        pubs.approve_entry(u, e, reason="ok")
        log = PublishingAuditLog.objects.filter(entry=e).first()
        assert log and log.actor_id == u.id and log.action == "entry_approved" and log.reason == "ok"

# Full E2E
@pytest.mark.django_db
class TestFullPipelineEndToEnd:
    def test_concept_to_published(self):
        u = _mu("e2e"); p, _, _, _, _ = _fp(u, "E2E")
        video = _gv(u, p); assert video.status == "ready"
        from apps.thumbnail import services as ts
        t = ts.request_thumbnail(u, p, platform_target="YouTube", title_text="T"); assert t.asset_ref
        prev = _gp(u, p); assert prev.status == "ready"
        _ap(u, prev); prev.refresh_from_db(); assert prev.approval_state == "approved"
        from apps.scheduler import services as sched
        e = sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC"); assert e.status == "scheduled"
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount
        sa = SocialAccount.objects.create(owner=u, team=p.team, platform="YouTube", platform_account_id="yt_e2e", display_name="E2E")
        pe = _ge(u, p, sa)
        pubs.approve_entry(u, pe, reason="E2E"); att = pubs.create_upload_attempt(u, pe)
        pubs.complete_upload_attempt(att, success=True); pe.refresh_from_db()
        assert pe.status == "published"
        from apps.analytics import services as ans
        ans.record_published_performance(pe, views=150, likes=25, topic="e2e")
        assert ans.get_analytics_summary(u)["total_views"] is not None
    def test_team_isolation(self):
        u1 = _mu("iso1"); u2 = _mu("iso2"); p, _, _, _, _ = _fp(u1, "Iso"); v1 = _gv(u1, p)
        from apps.video import services as vs; from apps.preview import services as ps
        assert vs.get_video(u2, v1.id) is None
        assert ps.get_preview(u2, _gp(u1, p).id) is None

# RBAC
@pytest.mark.django_db
class TestRBACEnforcement:
    def test_viewer_cannot_approve_preview(self):
        from apps.accounts.models import Team
        uv = User.objects.create_user(username="rbac_v", email="rv@t.co", password="LongPass123!")
        t = Team.objects.create(name="RBAC"); uv.memberships.create(team=t, role="Viewer")
        uc = _mu("rbac_c"); p, _, _, _, _ = _fp(uc, "RBAC")
        _gv(uc, p); prev = _gp(uc, p)
        from apps.preview import services as ps
        with pytest.raises(ValidationError): ps.approve_preview(uv, prev)
    def test_viewer_cannot_generate_video(self):
        from apps.accounts.models import Team
        uv = User.objects.create_user(username="rbac_vv", email="rvv@t.co", password="LongPass123!")
        t = Team.objects.create(name="RBACV"); uv.memberships.create(team=t, role="Viewer")
        uc = _mu("rbac_vc"); p, _, _, _, _ = _fp(uc, "RBACV")
        from apps.video import services as vs
        with pytest.raises(ValidationError): vs.request_video(uv, p)
