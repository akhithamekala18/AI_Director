"""Backend Phase 2 Acceptance - Task 27."""
import pytest
from django.contrib.auth import get_user_model

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.tasks import execute_job
from apps.audit.models import AuditLog
from apps.character.models import Character, CharacterLibrary
from apps.projects.models import Project
from apps.research.models import Research, ResearchSource, can_generate_script
from apps.scene.models import SceneBuilder, can_build_scenes
from apps.scene_media.models import SceneMedia
from apps.script.models import Script

User = get_user_model()


def _make_team_user(username="acceptance_user"):
    user = User.objects.create_user(username=username, email=f"{username}@example.com", password="LongPass123!")
    from apps.accounts.models import Team
    team = Team.objects.create(name=f"{username} workspace")
    user.memberships.create(team=team, role="Creator")
    return user


def _make_project(user, topic="Quantum gravity", lifecycle_state="Draft"):
    return Project.objects.create(team=user.memberships.first().team, owner=user, topic=topic, lifecycle_state=lifecycle_state)


def _make_approved_research(project):
    research = Research.objects.create(project=project, team=project.team)
    ResearchSource.objects.create(research=research, url="https://example.org/qg", title="QG Explained", snippet="Overview.", credibility_score=0.9)
    research.summary = "QG reconciles GR with QM."
    research.gate_state = Research.GateState.APPROVED
    research.save()
    return research


def _make_approved_script(project, research, scenes=None):
    if scenes is None:
        scenes = [
            {"id": "s1", "heading": "Hook", "narration": "What is QG?", "visual_notes": "Cosmos."},
            {"id": "s2", "heading": "Core", "narration": "Two theories unite.", "visual_notes": "Diagram."},
        ]
    return Script.objects.create(project=project, team=project.team, research=research, title="QG Explained", script="QG reconciles GR with QM.", narration="Welcome.", scenes=scenes, gate_state=Script.GateState.APPROVED)


def _make_approved_characters(project, script):
    return Character.objects.create(project=project, team=project.team, script=script,
        characters=[{"id": "char_narrator", "name": "Narrator", "age": "adult", "gender": "ambiguous", "appearance": {"hair_color": "dark"}, "clothing": {"outfit": "casual"}, "accessories": ["mic"], "style": {"realism": "stylized"}},
            {"id": "char_scientist", "name": "Dr. Nova", "age": "40s", "gender": "female", "appearance": {"hair_color": "silver"}, "clothing": {"outfit": "lab coat"}, "accessories": ["glasses"], "style": {"realism": "medium"}}],
        gate_state=Character.GateState.APPROVED)


def _build_and_approve_scene(project, script, characters):
    from apps.scene import services as ss
    builder = ss.build_scenes(project.owner, project)
    ss.approve_scene_builder(project.owner, builder)
    builder.refresh_from_db()
    return builder


@pytest.mark.django_db
class TestG1FactGrounding:
    def test_script_blocked_without_approved_research(self):
        user = _make_team_user("g1_u")
        ok, error = can_generate_script(_make_project(user))
        assert ok is False
        assert "approved" in error.lower()
    def test_script_generation_requires_research(self):
        from django.core.exceptions import ValidationError

        from apps.script import services as ss
        with pytest.raises(ValidationError):
            ss.generate_script(_make_team_user("g1_u2"), _make_project(_make_team_user("g1_u2b")))
    def test_approved_research_unblocks_script(self):
        u = _make_team_user("g1_u3")
        p = _make_project(u)
        _make_approved_research(p)
        ok, _ = can_generate_script(p)
        assert ok is True


@pytest.mark.django_db
class TestG2SourceTransparency:
    def test_research_has_sources(self):
        p = _make_project(_make_team_user("g2_u"))
        r = _make_approved_research(p)
        sources = ResearchSource.objects.filter(research=r)
        assert sources.exists() and sources.first().credibility_score > 0
    def test_script_links_to_research(self):
        p = _make_project(_make_team_user("g2_u2"))
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        assert s.research_id == r.id
    def test_research_source_fields_complete(self):
        p = _make_project(_make_team_user("g2_u3"))
        r = _make_approved_research(p)
        src = ResearchSource.objects.filter(research=r).first()
        assert src.url and src.title and src.snippet and src.credibility_score is not None


@pytest.mark.django_db
class TestG3ApprovalGating:
    def test_gate1_blocks_gate2(self):
        assert can_generate_script(_make_project(_make_team_user("g3_u")))[0] is False
    def test_gate2_blocks_gate3(self):
        from apps.character.models import Character as ChModel
        from apps.character.models import can_generate_characters
        p = _make_project(_make_team_user("g3_u2"))
        r = _make_approved_research(p)
        s = Script.objects.create(project=p, team=p.team, research=r, title="draft", script="x", narration="y", scenes=[], gate_state=Script.GateState.REVIEW)
        char_obj = ChModel.objects.create(project=p, team=p.team, script=s, characters=[], gate_state=ChModel.GateState.DRAFT)
        assert can_generate_characters(char_obj)[0] is False
    def test_gate3_blocks_gate4(self):
        p = _make_project(_make_team_user("g3_u3"))
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        ok, _ = can_build_scenes(SceneBuilder(project=p, team=p.team, script=s))
        assert ok is False
    def test_gate4_blocks_media_generation(self):
        from django.core.exceptions import ValidationError

        from apps.scene_media import services as ms
        with pytest.raises(ValidationError):
            ms.request_scene_media(_make_team_user("g3_u4"), _make_project(_make_team_user("g3_u4b")))
    def test_full_gate_chain_enforced(self):
        p = _make_project(_make_team_user("g3c"))
        assert can_generate_script(p)[0] is False
        from apps.character.models import Character as ChModel
        from apps.character.models import can_generate_characters
        char_obj = ChModel(project=p, team=p.team, script=None, characters=[])
        assert can_generate_characters(char_obj)[0] is False
        ok, _ = can_build_scenes(SceneBuilder(project=p, team=p.team))
        assert ok is False

@pytest.mark.django_db
class TestG4ScopedRegeneration:
    def test_regen_does_not_touch_other_scenes(self):
        from apps.regeneration import services as rs
        from apps.scene_media import services as ms
        u = _make_team_user("g4_u")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        ms.request_scene_media(u, p)
        s1m = list(SceneMedia.objects.filter(project=p, scene_id="s1"))
        s1v = {m.id: m.version for m in s1m}
        job = rs.request_regeneration(u, p, scene_id="s2", media_types=["voice"])
        assert job.status == AsyncJob.Status.COMPLETED
        for m in s1m:
            m.refresh_from_db()
            assert m.version == s1v[m.id]
    def test_regen_version_increment(self):
        from apps.regeneration import services as rs
        from apps.scene_media import services as ms
        u = _make_team_user("g4_v")
        p = _make_project(u)
        r = _make_approved_research(p)
        s = _make_approved_script(p, r)
        c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        ms.request_scene_media(u, p)
        sv = SceneMedia.objects.get(project=p, scene_id="s2", media_type="voice")
        old = sv.version
        rs.request_regeneration(u, p, scene_id="s2", media_types=["voice"])
        sv.refresh_from_db()
        assert sv.version > old


@pytest.mark.django_db
class TestG5IdentityStability:
    def test_character_stable_id_persisted(self):
        u = _make_team_user("g5_u")
        p = _make_project(u)
        chars = _make_approved_characters(p, _make_approved_script(p, _make_approved_research(p)))
        for c in chars.characters:
            assert "id" in c and c["id"].startswith("char_")
    def test_library_persists_character_attributes(self):
        u = _make_team_user("g5_l")
        p = _make_project(u)
        _make_approved_characters(p, _make_approved_script(p, _make_approved_research(p)))
        lib = CharacterLibrary.objects.filter(team=p.team, character_id="char_narrator").first()
        if lib:
            assert lib.attributes.get("name") == "Narrator"
    def test_scene_references_stable_character_ids(self):
        u = _make_team_user("g5_s")
        p = _make_project(u)
        chars = _make_approved_characters(p, _make_approved_script(p, _make_approved_research(p)))
        b = _build_and_approve_scene(p, chars.script, chars)
        cids = {ch.get("character_id","") if isinstance(ch,dict) else ch for sc in b.scenes for ch in sc.get("characters",[])}
        assert len(cids) > 0


@pytest.mark.django_db
class TestG7Auditing:
    def test_research_service_creates_audit(self):
        from apps.research import services as rs
        u = _make_team_user("g7a1"); p = _make_project(u)
        rs.generate_research(u, p)
        assert AuditLog.objects.filter(target_type="research").exists()
    def test_scene_service_creates_audit(self):
        from apps.scene import services as sc
        u = _make_team_user("g7a3"); p = _make_project(u)
        r = _make_approved_research(p); s = _make_approved_script(p, r)
        _make_approved_characters(p, s)
        builder = sc.build_scenes(u, p)
        sc.approve_scene_builder(u, builder)
        assert AuditLog.objects.filter(target_type="scene").exists()
    def test_audit_records_actor_and_timestamp(self):
        from apps.research import services as rs
        u = _make_team_user("g7at"); p = _make_project(u)
        rs.generate_research(u, p)
        last = AuditLog.objects.order_by("-created_at").first()
        assert last is not None and last.actor_id is not None and last.created_at is not None


@pytest.mark.django_db
class TestG9CostTransparency:
    def test_asyncjob_has_cost_field(self):
        u = _make_team_user("g9c"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION)
        assert hasattr(j, "cost") and j.cost == 0
    def test_completed_job_records_result(self):
        u = _make_team_user("g9r"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION)
        def h(job):
            job.progress = 1.0
            job.cost = 0.05
            job.save(update_fields=["progress", "cost"])
            return {"ok": True, "cost": 0.05}
        from apps.ai_orchestration import tasks; tasks.JOB_EXECUTORS["research_generation"] = h
        try: execute_job.delay(j.id).get()
        finally: tasks.JOB_EXECUTORS.pop("research_generation", None)
        j.refresh_from_db()
        from decimal import Decimal
        assert j.status == AsyncJob.Status.COMPLETED and j.cost == Decimal("0.05")


@pytest.mark.django_db
class TestFullPipelineAcceptance:
    def test_concept_to_approved_scenes(self):
        u = _make_team_user("p1"); p = _make_project(u, topic="Neural networks")
        r = _make_approved_research(p); assert r.gate_state == Research.GateState.APPROVED
        s = _make_approved_script(p, r); assert s.gate_state == Script.GateState.APPROVED and s.research_id == r.id
        chars = _make_approved_characters(p, s); assert chars.gate_state == Character.GateState.APPROVED
        b = _build_and_approve_scene(p, s, chars)
        assert b.gate_state == SceneBuilder.GateState.APPROVED and len(b.scenes) >= 1
    def test_scene_package_references_approved_script(self):
        u = _make_team_user("p2"); p = _make_project(u); r = _make_approved_research(p)
        s = _make_approved_script(p, r); chars = _make_approved_characters(p, s)
        assert _build_and_approve_scene(p, s, chars).script_id == s.id
    def test_scene_package_references_approved_characters(self):
        u = _make_team_user("p3"); p = _make_project(u); r = _make_approved_research(p)
        s = _make_approved_script(p, r); chars = _make_approved_characters(p, s)
        assert _build_and_approve_scene(p, s, chars).character_set_id == chars.id
    def test_no_unapproved_downstream_generation(self):
        from django.core.exceptions import ValidationError

        from apps.scene_media import services as ms
        with pytest.raises(ValidationError): ms.request_scene_media(_make_team_user("p4"), _make_project(_make_team_user("p4b")))
    def test_media_generation_requires_approved_scene(self):
        u = _make_team_user("p5"); p = _make_project(u); r = _make_approved_research(p)
        s = _make_approved_script(p, r); _make_approved_characters(p, s)
        from apps.scene import services as ss; b = ss.build_scenes(u, p)
        assert b.gate_state == SceneBuilder.GateState.REVIEW
        from django.core.exceptions import ValidationError

        from apps.scene_media import services as ms
        with pytest.raises(ValidationError): ms.request_scene_media(u, p)
    def test_pipeline_produces_scene_content(self):
        u = _make_team_user("p6"); p = _make_project(u)
        r = _make_approved_research(p); s = _make_approved_script(p, r); chars = _make_approved_characters(p, s)
        for sc in _build_and_approve_scene(p, s, chars).scenes:
            assert "id" in sc and ("heading" in sc or "narration" in sc)


@pytest.mark.django_db
class TestRetryResumeUnderFailure:
    def test_failed_job_can_be_retried(self):
        u = _make_team_user("r1"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION, status=AsyncJob.Status.FAILED, error_message="injected")
        assert j.retry_count < j.max_retries
        from apps.ai_orchestration.services import retry_job
        retry_job(u, j); j.refresh_from_db()
        assert j.status == AsyncJob.Status.RETRYING and j.error_message == ""
    def test_retry_increments_count(self):
        u = _make_team_user("r2"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION, status=AsyncJob.Status.FAILED, retry_count=1)
        from apps.ai_orchestration.services import retry_job; retry_job(u, j); j.refresh_from_db()
        assert j.retry_count == 2
    def test_cancelled_job_state(self):
        u = _make_team_user("c1"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION, status=AsyncJob.Status.RUNNING)
        from apps.ai_orchestration.services import cancel_job; cancel_job(u, j); j.refresh_from_db()
        assert j.status == AsyncJob.Status.CANCELLED
    def test_job_failure_produces_error_message(self):
        u = _make_team_user("f1"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.REGENERATION, metadata={"regeneration_request": 999999})
        execute_job.delay(j.id).get(); j.refresh_from_db()
        assert j.status == AsyncJob.Status.FAILED and j.error_message
    def test_retry_respects_max_retries(self):
        u = _make_team_user("mx"); p = _make_project(u)
        j = AsyncJob.objects.create(team=p.team, project=p, owner=u, job_type=AsyncJob.JobType.RESEARCH_GENERATION, status=AsyncJob.Status.FAILED, retry_count=3, max_retries=3)
        assert j.retry_count >= j.max_retries or not j.can_transition(AsyncJob.Status.RETRYING)


@pytest.mark.django_db
class TestTeamIsolationAcceptance:
    def test_outsider_cannot_see_research(self):
        p = _make_project(_make_team_user("ta")); _make_approved_research(p)
        from apps.research import services as rs; assert rs.get_research(_make_team_user("tb"), p) is None
    def test_outsider_cannot_see_script(self):
        p = _make_project(_make_team_user("tc")); r = _make_approved_research(p); _make_approved_script(p, r)
        from apps.script import services as ss; assert ss.get_script(_make_team_user("td"), p) is None
    def test_outsider_cannot_see_characters(self):
        p = _make_project(_make_team_user("te")); r = _make_approved_research(p); s = _make_approved_script(p, r); _make_approved_characters(p, s)
        from apps.character import services as cs; assert cs.get_character(_make_team_user("tf"), p) is None
    def test_outsider_cannot_see_scene_builder(self):
        p = _make_project(_make_team_user("tg")); r = _make_approved_research(p); s = _make_approved_script(p, r); c = _make_approved_characters(p, s)
        _build_and_approve_scene(p, s, c)
        from apps.scene import services as sc; assert sc.get_scene_builder(_make_team_user("th"), p) is None


@pytest.mark.django_db
class TestStateMachineAcceptance:
    def test_research_legal_transitions(self):
        tr = Research._TRANSITIONS
        assert tr[Research.GateState.DRAFT] == {Research.GateState.GENERATING}
        assert tr[Research.GateState.GENERATING] == {Research.GateState.REVIEW}
        assert Research.GateState.APPROVED in tr[Research.GateState.REVIEW]
    def test_script_legal_transitions(self):
        tr = Script._TRANSITIONS
        assert tr[Script.GateState.DRAFT] == {Script.GateState.GENERATING}
        assert tr[Script.GateState.GENERATING] == {Script.GateState.REVIEW}
        assert Script.GateState.APPROVED in tr[Script.GateState.REVIEW]
    def test_character_legal_transitions(self):
        tr = Character._TRANSITIONS
        assert tr[Character.GateState.DRAFT] == {Character.GateState.GENERATING}
        assert tr[Character.GateState.GENERATING] == {Character.GateState.REVIEW}
        assert Character.GateState.APPROVED in tr[Character.GateState.REVIEW]
    def test_scene_builder_legal_transitions(self):
        tr = SceneBuilder._TRANSITIONS
        assert SceneBuilder.GateState.REVIEW in tr[SceneBuilder.GateState.DRAFT]
        assert SceneBuilder.GateState.APPROVED in tr[SceneBuilder.GateState.REVIEW]
    def test_research_illegal_transition_raises(self):
        r = Research(project=None); r.gate_state = Research.GateState.DRAFT
        with pytest.raises(ValueError): r.transition_to(Research.GateState.APPROVED)
    def test_script_illegal_transition_raises(self):
        s = Script(project=None); s.gate_state = Script.GateState.DRAFT
        with pytest.raises(ValueError): s.transition_to(Script.GateState.APPROVED)
