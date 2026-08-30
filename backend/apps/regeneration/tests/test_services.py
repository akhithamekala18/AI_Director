# -*- coding: utf-8 -*-
"""Service-layer tests for regeneration."""
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.ai_orchestration.models import AsyncJob
from apps.audit.models import AuditLog
from apps.regeneration import services
from apps.regeneration.models import RegenerationRequest, SceneMediaVersion
from apps.scene_media.models import SceneMedia

from .helpers import approved_scene_builder, make_project, setup_media


@pytest.mark.django_db
class TestTeamIsolation:
    def test_member_can_list(self, make_user):
        user = make_user(username="svc_member")
        project = make_project(user)
        setup_media(user, project)
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        listing = services.list_regeneration_requests(user, project)
        assert listing.count() >= 1

    def test_outsider_list_is_empty(self, make_user):
        owner = make_user(username="svc_own")
        outsider = make_user(username="svc_out")
        project = make_project(owner)
        setup_media(owner, project)
        services.request_regeneration(owner, project, scene_id="s1", media_types=["voice"])
        assert services.list_regeneration_requests(outsider, project).count() == 0

    def test_outsider_get_returns_none(self, make_user):
        owner = make_user(username="svc_own2")
        outsider = make_user(username="svc_out2")
        project = make_project(owner)
        setup_media(owner, project)
        services.request_regeneration(owner, project, scene_id="s1", media_types=["voice"])
        req = services.list_regeneration_requests(owner, project).first()
        assert req is not None
        assert services.get_regeneration_request(outsider, req.id) is None


@pytest.mark.django_db
class TestGate4Dependency:
    def test_no_builder_rejected(self, make_user):
        user = make_user(username="svc_nobuild")
        project = make_project(user)
        with pytest.raises(DjangoValidationError, match="approved scene package"):
            services.request_regeneration(user, project, scene_id="s1")

    def test_review_state_rejected(self, make_user):
        from apps.scene import services as scene_services
        from apps.scene.tests.helpers import approved_characters, approved_script
        user = make_user(username="svc_review")
        project = make_project(user)
        script = approved_script(user, project)
        approved_characters(user, project, script)
        scene_services.build_scenes(user, project)
        with pytest.raises(DjangoValidationError, match="approved scene package"):
            services.request_regeneration(user, project, scene_id="s1")

    def test_non_member_rejected(self, make_user):
        user = make_user(username="svc_nonmem")
        other = make_user(username="svc_other")
        project = make_project(user)
        setup_media(user, project)
        with pytest.raises(DjangoValidationError, match="not a member"):
            services.request_regeneration(other, project, scene_id="s1")


@pytest.mark.django_db
class TestScopeValidation:
    def test_missing_scene_id_rejected(self, make_user):
        user = make_user(username="svc_noscope")
        project = make_project(user)
        setup_media(user, project)
        with pytest.raises(DjangoValidationError, match="scene_id is required"):
            services.request_regeneration(user, project, scene_id=None, full=False)

    def test_invalid_scene_id_rejected(self, make_user):
        user = make_user(username="svc_badscene")
        project = make_project(user)
        setup_media(user, project)
        with pytest.raises(DjangoValidationError, match="does not exist"):
            services.request_regeneration(user, project, scene_id="nonexistent")

    def test_no_media_rejected(self, make_user):
        user = make_user(username="svc_nomedia")
        project = make_project(user)
        approved_scene_builder(user, project)
        with pytest.raises(DjangoValidationError, match="no scene media"):
            services.request_regeneration(user, project, scene_id="s1")


@pytest.mark.django_db
class TestRequestRegeneration:
    def test_creates_job_and_request(self, make_user):
        user = make_user(username="svc_req")
        project = make_project(user)
        setup_media(user, project)
        job = services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        assert job is not None
        assert job.job_type == AsyncJob.JobType.REGENERATION
        assert job.status == AsyncJob.Status.COMPLETED
        reqs = services.list_regeneration_requests(user, project)
        assert reqs.count() >= 1
        req = reqs.first()
        assert req.async_job_id == job.id
        assert req.scene_id == "s1"
        assert req.media_types == ["voice"]

    def test_audit_records_written(self, make_user):
        user = make_user(username="svc_audit")
        project = make_project(user)
        setup_media(user, project)
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        assert AuditLog.objects.filter(reason="regeneration_requested").exists()


@pytest.mark.django_db
class TestSnapshotAndLineage:
    def test_snapshots_created(self, make_user):
        user = make_user(username="svc_snap")
        project = make_project(user)
        setup_media(user, project)
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        req = services.list_regeneration_requests(user, project).first()
        snaps = SceneMediaVersion.objects.filter(regeneration=req)
        assert snaps.count() >= 1

    def test_old_media_preserved(self, make_user):
        user = make_user(username="svc_preserve")
        project = make_project(user)
        setup_media(user, project)
        original = SceneMedia.objects.filter(project=project, scene_id="s1", media_type="voice").first()
        original_asset = original.asset_ref
        original_narration = original.narration
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        snap = SceneMediaVersion.objects.filter(media=original, regeneration__isnull=False).first()
        assert snap is not None
        assert snap.asset_ref == original_asset
        assert snap.narration == original_narration

    def test_version_incremented(self, make_user):
        user = make_user(username="svc_version")
        project = make_project(user)
        setup_media(user, project)
        media = SceneMedia.objects.filter(project=project, scene_id="s1", media_type="voice").first()
        old_version = media.version
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        media.refresh_from_db()
        assert media.version > old_version

    def test_other_scene_untouched(self, make_user):
        user = make_user(username="svc_blast")
        project = make_project(user)
        setup_media(user, project)
        s2_media = SceneMedia.objects.filter(project=project, scene_id="s2").first()
        s2_version_before = s2_media.version
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        s2_media.refresh_from_db()
        assert s2_media.version == s2_version_before


@pytest.mark.django_db
class TestRunRegeneration:
    def test_completes(self, make_user):
        user = make_user(username="svc_run")
        project = make_project(user)
        setup_media(user, project)
        services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        req = services.list_regeneration_requests(user, project).first()
        assert req.status == RegenerationRequest.Status.COMPLETED
        assert req.media_snapshot_version >= 1

    def test_result_structure(self, make_user):
        user = make_user(username="svc_struct")
        project = make_project(user)
        setup_media(user, project)
        job = services.request_regeneration(user, project, scene_id="s1", media_types=["voice"])
        req = services.list_regeneration_requests(user, project).first()
        assert req.status == RegenerationRequest.Status.COMPLETED
        assert job.result["regeneration_request"] == req.id
        assert job.result["status"] == "completed"
        assert "regenerated_ids" in job.result
        assert len(job.result["regenerated_ids"]) >= 1
