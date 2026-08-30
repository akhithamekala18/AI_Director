# -*- coding: utf-8 -*-
"""Service-layer tests for scene media: team isolation, idempotency, audit."""
import pytest
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.audit.models import AuditLog
from apps.scene_media import services
from apps.scene_media.providers.fake import FakeSceneMediaProvider

from .helpers import approved_scene_builder, make_project


@pytest.mark.django_db
class TestTeamIsolation:
    def test_member_can_list_and_get(self, make_user):
        user = make_user(username="svc_member")
        project = make_project(user)
        approved_scene_builder(user, project)
        services.request_scene_media(user, project)
        listing = services.list_scene_media(user, project)
        assert listing.count() == 8
        media = listing.first()
        assert services.get_scene_media(user, media.id).id == media.id

    def test_outsider_list_is_empty(self, make_user):
        owner = make_user(username="svc_owner")
        outsider = make_user(username="svc_outsider")
        project = make_project(owner)
        approved_scene_builder(owner, project)
        services.request_scene_media(owner, project)
        assert services.list_scene_media(outsider, project).count() == 0

    def test_outsider_get_returns_none(self, make_user):
        owner = make_user(username="svc_owner2")
        outsider = make_user(username="svc_outsider2")
        project = make_project(owner)
        approved_scene_builder(owner, project)
        services.request_scene_media(owner, project)
        media = services.list_scene_media(owner, project).first()
        assert media is not None
        assert services.get_scene_media(outsider, media.id) is None


@pytest.mark.django_db
class TestJobAndPersistence:
    def test_request_stores_metadata_and_persists_media(self, make_user):
        user = make_user(username="svc_req")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = services.request_scene_media(user, project, media_types=["voice", "music"])
        assert job.metadata["media_types"] == ["voice", "music"]
        assert job.metadata["scene_count"] == 2
        # eager run persisted 2 scenes x 2 requested types
        media = services.list_scene_media(user, project)
        assert media.count() == 4
        assert {m.media_type for m in media} == {"voice", "music"}
        # ordering + stable scene ids preserved
        orders = [(m.scene_id, m.scene_order) for m in media]
        assert ("s1", 1) in orders and ("s2", 2) in orders
        assert all(m.characters for m in media)  # G-5 stable character ids

    def test_run_generation_is_idempotent_on_retry(self, make_user):
        user = make_user(username="svc_retry")
        project = make_project(user)
        approved_scene_builder(user, project)
        job = services.request_scene_media(user, project)
        assert services.list_scene_media(user, project).count() == 8

        # simulate a retry: run the handler again
        result = services.run_generation(job, provider=FakeSceneMediaProvider())
        assert result["count"] == 8
        assert services.list_scene_media(user, project).count() == 8  # no duplicates
        # version incremented on the re-run rows
        media = services.list_scene_media(user, project).first()
        media.refresh_from_db()
        assert media.version == 2

    def test_empty_media_types_rejected(self, make_user):
        user = make_user(username="svc_notypes")
        project = make_project(user)
        approved_scene_builder(user, project)
        with pytest.raises(DjangoValidationError):
            services.request_scene_media(user, project, media_types=["bogus"])

    def test_audit_records_written(self, make_user):
        user = make_user(username="svc_audit")
        project = make_project(user)
        approved_scene_builder(user, project)
        services.request_scene_media(user, project)
        assert AuditLog.objects.filter(reason="scene_media_generation_requested").exists()
        assert AuditLog.objects.filter(reason="scene_media_generated").count() == 8
