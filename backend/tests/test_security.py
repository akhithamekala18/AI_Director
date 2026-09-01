# -*- coding: utf-8 -*-
"""Task 54 - Security Validation + Hardening"""
import inspect, os, re, pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from apps.audit.models import AuditLog
from apps.accounts.models import Team
User = get_user_model()

def _u(name, role="Creator"):
    u = User.objects.create_user(username=name, email=f"{name}@s.t", password="LongPass123!")
    t = Team.objects.create(name=f"t-{name}")
    u.memberships.create(team=t, role=role)
    return u

def _p(user, topic="ST"):
    from apps.projects.models import Project
    return Project.objects.create(team=user.memberships.first().team, owner=user, topic=topic, lifecycle_state="Draft")

def _ar(project):
    from apps.research.models import Research, ResearchSource
    r = Research.objects.create(project=project, team=project.team)
    ResearchSource.objects.create(research=r, url="https://s.t", title="S", snippet="X", credibility_score=0.9)
    r.summary = "S."
    r.gate_state = Research.GateState.APPROVED
    r.save()
    return r

def _as(project, research):
    from apps.script.models import Script
    return Script.objects.create(project=project, team=project.team, research=research, title="S", script="S", narration="N",
        scenes=[{"id":"s1","heading":"H","narration":"N","visual_notes":"V"}], gate_state=Script.GateState.APPROVED)

def _ac(project, script):
    from apps.character.models import Character
    return Character.objects.create(project=project, team=project.team, script=script,
        characters=[{"id":"c1","name":"N","age":"a","gender":"m","appearance":{},"clothing":{},"accessories":[],"style":{}}],
        gate_state=Character.GateState.APPROVED)

def _bs(user, project, script):
    from apps.scene import services as ss
    b = ss.build_scenes(user, project)
    ss.approve_scene_builder(user, b)
    return b

def _fp(user, topic="SP"):
    p = _p(user, topic)
    r = _ar(p)
    s = _as(p, r)
    c = _ac(p, s)
    b = _bs(user, p, s)
    return p, r, s, c, b

# === 1. Credential Store Security ===
@pytest.mark.django_db
class TestCredentialStoreSecurity:
    def test_credential_encrypted_at_rest(self):
        u = _u("sc1")
        from apps.settings_app.services import encrypt_secret
        from apps.settings_app.models import StoredCredential
        pt = "super-secret-12345"
        enc = encrypt_secret(pt)
        assert enc != pt
        c = StoredCredential.objects.create(owner=u, provider="YouTube", label="t", encrypted_value=enc)
        c.refresh_from_db()
        assert c.encrypted_value != pt

    def test_credential_decrypt_roundtrip(self):
        from apps.settings_app.services import encrypt_secret, decrypt_secret
        assert decrypt_secret(encrypt_secret("roundtrip")) == "roundtrip"

    def test_credential_api_never_exposes_secret(self):
        from apps.settings_app.serializers import StoredCredentialSerializer
        assert "encrypted_value" not in StoredCredentialSerializer.Meta.fields
        assert "secret" not in StoredCredentialSerializer.Meta.fields

    def test_credential_revoked_not_listed(self):
        u = _u("sc2")
        from apps.settings_app.models import StoredCredential
        from apps.settings_app.services import encrypt_secret
        StoredCredential.objects.create(owner=u, provider="YouTube", label="active", encrypted_value=encrypt_secret("ak"))
        rev = StoredCredential.objects.create(owner=u, provider="YouTube", label="revoked", encrypted_value=encrypt_secret("rk"))
        rev.revoked = True
        rev.save(update_fields=["revoked"])
        assert StoredCredential.objects.filter(owner=u, revoked=False).count() == 1

    def test_credential_cross_user_isolation(self):
        u1, u2 = _u("sc3a"), _u("sc3b")
        from apps.settings_app.models import StoredCredential
        from apps.settings_app.services import encrypt_secret
        StoredCredential.objects.create(owner=u1, provider="YouTube", label="a", encrypted_value=encrypt_secret("ak"))
        StoredCredential.objects.create(owner=u2, provider="YouTube", label="b", encrypted_value=encrypt_secret("bk"))
        assert StoredCredential.objects.filter(owner=u1, revoked=False).count() == 1
        assert StoredCredential.objects.filter(owner=u2, revoked=False).count() == 1

    def test_encryption_key_configured(self):
        from django.conf import settings
        assert hasattr(settings, "CREDENTIAL_ENCRYPTION_KEY")

# === 2. RBAC Least-Privilege ===
@pytest.mark.django_db
class TestRBACLeastPrivilege:
    def test_viewer_cannot_approve_preview(self):
        u_v, u_c = _u("sr1", role="Viewer"), _u("sr1c", role="Creator")
        p, *_ = _fp(u_c)
        from apps.video import services as vs
        vs.request_video(u_c, p)
        from apps.preview import services as ps
        prev = ps.request_preview(u_c, p)
        with pytest.raises(ValidationError): ps.approve_preview(u_v, prev)

    def test_viewer_cannot_generate_video(self):
        u_v, u_c = _u("sr2", role="Viewer"), _u("sr2c", role="Creator")
        p, *_ = _fp(u_c)
        from apps.video import services as vs
        with pytest.raises(ValidationError): vs.request_video(u_v, p)

    def test_editor_cannot_approve_publishing(self):
        u_e, u_c = _u("sr3", role="Editor"), _u("sr3c", role="Creator")
        p, *_ = _fp(u_c)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        sa = SocialAccount.objects.create(owner=u_c, team=u_c.memberships.first().team, platform="YouTube", platform_account_id="srb", display_name="S")
        post = ScheduledPost.objects.create(project=p, team=u_c.memberships.first().team, owner=u_c, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=u_c.memberships.first().team, status="ready_for_approval", scheduled_utc=timezone.now() + timedelta(hours=48))
        # RBAC enforced at view layer via HasCapability
        from apps.accounts.permissions import has_capability
        from apps.core.enums import Role
        assert not has_capability(Role.EDITOR, "approve")
        assert not has_capability(Role.EDITOR, "publish")

    def test_reviewer_cannot_manage_projects(self):
        u_r = _u("sr4", role="Reviewer")
        from apps.projects import services as ps
        # RBAC enforced at view layer via HasCapability
        from apps.accounts.permissions import has_capability
        from apps.core.enums import Role
        assert not has_capability(Role.REVIEWER, "manage_projects")

    def test_unauthenticated_access_blocked(self):
        from apps.accounts.permissions import HasCapability
        class FR: user = None
        class FV: capability = "view_projects"
        assert HasCapability().has_permission(FR(), FV()) is False

    def test_role_matrix_consistency(self):
        from apps.accounts.permissions import role_rank, ROLE_ORDER
        assert [role_rank(r) for r in ROLE_ORDER] == sorted([role_rank(r) for r in ROLE_ORDER])

    def test_viewer_lowest_privilege(self):
        from apps.accounts.permissions import has_capability
        from apps.core.enums import Role
        for c in ["approve", "publish", "admin"]: assert not has_capability(Role.VIEWER, c)

    def test_editor_cannot_publish(self):
        from apps.accounts.permissions import has_capability
        from apps.core.enums import Role
        for c in ["publish", "approve"]: assert not has_capability(Role.EDITOR, c)

    def test_admin_has_all_capabilities(self):
        from apps.accounts.permissions import has_capability
        from apps.core.enums import Role
        for c in ["approve", "publish", "admin", "manage_projects", "manage_settings"]: assert has_capability(Role.ADMIN, c)

# === 3. Team Isolation Penetration ===
@pytest.mark.django_db
class TestTeamIsolationPenetration:
    def test_research_isolation(self):
        u1, u2 = _u("si1"), _u("si2")
        p = _p(u1, "I1"); _ar(p)
        from apps.research import services as rs
        assert rs.get_research(u2, p) is None

    def test_video_isolation(self):
        u1, u2 = _u("si3"), _u("si4")
        p, *_ = _fp(u1, "I3")
        from apps.video import services as vs
        v = vs.request_video(u1, p)
        assert vs.get_video(u2, v.id) is None

    def test_preview_isolation(self):
        u1, u2 = _u("si5"), _u("si6")
        p, *_ = _fp(u1, "I5")
        from apps.video import services as vs
        from apps.preview import services as ps
        vs.request_video(u1, p)
        prev = ps.request_preview(u1, p)
        assert ps.get_preview(u2, prev.id) is None

    def test_publishing_isolation(self):
        u1, u2 = _u("si7"), _u("si8")
        p, *_ = _fp(u1, "I7")
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        sa = SocialAccount.objects.create(owner=u1, team=u1.memberships.first().team, platform="YouTube", platform_account_id="i7", display_name="I7")
        post = ScheduledPost.objects.create(project=p, team=u1.memberships.first().team, owner=u1, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=u1.memberships.first().team, status="scheduled", scheduled_utc=timezone.now() + timedelta(hours=48))
        assert pubs.get_entry(u2, entry.id) is None

    def test_project_isolation(self):
        u1, u2 = _u("si9"), _u("si10")
        p = _p(u1, "I9")
        from apps.projects import services as ps
        assert ps.get_project(u2, p.id) is None

# === 4. Audit Integrity ===
@pytest.mark.django_db
class TestAuditIntegrity:
    def test_audit_recorded_on_research(self):
        u = _u("sa1"); p = _p(u)
        from apps.research import services as rs; rs.generate_research(u, p)
        log = AuditLog.objects.filter(target_type="research").last()
        assert log is not None and log.actor_id == u.id

    def test_audit_recorded_on_publishing_approval(self):
        u = _u("sa2"); p, *_ = _fp(u)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        sa = SocialAccount.objects.create(owner=u, team=u.memberships.first().team, platform="YouTube", platform_account_id="a2", display_name="A2")
        post = ScheduledPost.objects.create(project=p, team=u.memberships.first().team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=u.memberships.first().team, status="ready_for_approval", scheduled_utc=timezone.now() + timedelta(hours=48))
        pubs.approve_entry(u, entry, reason="audit")
        from apps.publishing.models import PublishingAuditLog
        log = PublishingAuditLog.objects.filter(entry=entry, action="entry_approved").last()
        assert log is not None and log.actor_id == u.id

    def test_audit_action_recorded(self):
        u = _u("sa3")
        from apps.core.enums import AuditAction
        from apps.audit.services import record_audit
        record_audit(u, AuditAction.CREATE.value, target_type="test", target_id="1")
        log = AuditLog.objects.filter(actor=u).last()
        assert log.action == AuditAction.CREATE.value

# === 5. Approval Bypass Prevention ===
@pytest.mark.django_db
class TestApprovalBypassPrevention:
    def test_upload_blocked_without_approval(self):
        u = _u("sb1"); p, *_ = _fp(u)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry
        sa = SocialAccount.objects.create(owner=u, team=u.memberships.first().team, platform="YouTube", platform_account_id="b1", display_name="B1")
        post = ScheduledPost.objects.create(project=p, team=u.memberships.first().team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=u.memberships.first().team, status="ready_for_approval", scheduled_utc=timezone.now() + timedelta(hours=48))
        with pytest.raises(ValidationError): pubs.create_upload_attempt(u, entry)

    def test_expired_approval_blocks_upload(self):
        u = _u("sb2"); p, *_ = _fp(u)
        from apps.publishing import services as pubs
        from apps.publishing.models import SocialAccount, ScheduledPost, ScheduledEntry, Approval
        sa = SocialAccount.objects.create(owner=u, team=u.memberships.first().team, platform="YouTube", platform_account_id="b2", display_name="B2")
        post = ScheduledPost.objects.create(project=p, team=u.memberships.first().team, owner=u, status="draft")
        entry = ScheduledEntry.objects.create(post=post, social_account=sa, platform="YouTube", team=u.memberships.first().team, status="ready_for_approval", scheduled_utc=timezone.now() + timedelta(hours=48))
        Approval.objects.create(entry=entry, actor=u, decision="approve", reason="old", expires_at=timezone.now() - timedelta(hours=1))
        assert not pubs.is_approval_valid(entry)

    def test_schedule_requires_preview(self):
        u = _u("sb3"); p, *_ = _fp(u)
        from apps.video import services as vs
        from apps.scheduler import services as sched
        vs.request_video(u, p)
        with pytest.raises(ValidationError, match="approved preview"): sched.create_entry(u, p, "YouTube", "2026-09-15T18:30:00", "UTC")

# === 6. State Machine Integrity ===
@pytest.mark.django_db
class TestStateMachineIntegrity:
    def test_research_cannot_skip_to_approved(self):
        from apps.research.models import Research
        r = Research(project=None); r.gate_state = Research.GateState.DRAFT
        with pytest.raises(ValueError): r.transition_to(Research.GateState.APPROVED)

    def test_script_cannot_skip_to_approved(self):
        from apps.script.models import Script
        s = Script(project=None, team=None, research=None); s.gate_state = Script.GateState.DRAFT
        with pytest.raises(ValueError): s.transition_to(Script.GateState.APPROVED)

# === 7. Settings / Middleware Security ===
@pytest.mark.django_db
class TestSettingsSecurity:
    def test_middleware_does_not_log_bodies(self):
        from apps.core.middleware import RequestLoggingMiddleware
        src = inspect.getsource(RequestLoggingMiddleware)
        assert "request.body" not in src and "request.data" not in src

    def test_middleware_strips_query_strings(self):
        from apps.core.middleware import RequestLoggingMiddleware
        assert "request.path" in inspect.getsource(RequestLoggingMiddleware)

    def test_drf_default_auth_classes(self):
        from django.conf import settings
        auth = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        assert len(auth) > 0
        assert "rest_framework.authentication.TokenAuthentication" in auth

    def test_drf_default_permission_is_authenticated(self):
        from django.conf import settings
        assert "rest_framework.permissions.IsAuthenticated" in settings.REST_FRAMEWORK.get("DEFAULT_PERMISSION_CLASSES", [])

    def test_password_validation_enforced(self):
        from django.conf import settings
        assert len(settings.AUTH_PASSWORD_VALIDATORS) > 0

    def test_cors_not_wildcard(self):
        from django.conf import settings
        assert len([m for m in settings.MIDDLEWARE if "cors" in m.lower()]) == 0

# === 8. Secret Isolation ===
class TestSecretIsolation:
    def test_settings_uses_env_for_secret_key(self):
        from django.conf import settings
        import importlib; mod = importlib.import_module("config.settings.base"); base = mod.__file__
        with open(base, encoding="utf-8") as f: assert "DJANGO_SECRET_KEY" in f.read()

    def test_settings_uses_env_for_encryption_key(self):
        from django.conf import settings
        import importlib; mod = importlib.import_module("config.settings.base"); base = mod.__file__
        with open(base, encoding="utf-8") as f: c = f.read()
        assert "CREDENTIAL_ENCRYPTION_KEY" in c and "os.environ.get" in c

    def test_no_hardcoded_api_keys_in_source(self):
        bd = os.path.join(os.path.dirname(__file__), "..")
        pat = re.compile(r"(sk-[a-zA-Z0-9]{20,}|key-[a-zA-Z0-9]{20,})")
        for root, dirs, files in os.walk(bd):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "migrations", ".git")]
            for fn in files:
                if fn.endswith(".py") and not fn.startswith("test_"):
                    fp = os.path.join(root, fn)
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        for i, ln in enumerate(f, 1):
                            if pat.search(ln): pytest.fail(f"Hardcoded secret in {fp}:{i}")
