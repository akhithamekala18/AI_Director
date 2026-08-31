# -*- coding: utf-8 -*-
"""Scheduler API tests (Task 38)."""
import pytest
from rest_framework.test import APIClient


def _create_youtube_preview(auth_client, project):
    """Helper to create and approve a YouTube preview."""
    from apps.preview.services import request_preview, approve_preview
    # First generate video for YouTube
    from apps.video.services import request_video
    request_video(project.owner, project, "YouTube")
    # Then generate and approve preview
    preview = request_preview(project.owner, project, "YouTube")
    approve_preview(project.owner, preview)


@pytest.mark.django_db
class TestScheduleCreateAPI:
    def test_create_schedule_success(self, auth_client, project, approved_preview):
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data["success"] is True
        entry = data["data"]["entry"]
        assert entry["platform"] == "YouTube"
        assert entry["status"] == "scheduled"
        assert entry["timezone"] == "Asia/Kolkata"
        assert entry["version"] == 1

    def test_create_schedule_no_preview(self, auth_client, project, approved_video):
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_schedule_duplicate_platform(self, auth_client, project, approved_preview):
        auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-16T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        assert resp.status_code == 400

    def test_create_schedule_unauthorized(self, project):
        anon = APIClient()
        resp = anon.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00"},
            format="json",
        )
        assert resp.status_code == 403

    def test_timezone_normalization_utc(self, auth_client, project, approved_preview):
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "UTC"},
            format="json",
        )
        assert resp.status_code == 200
        entry = resp.json()["data"]["entry"]
        assert entry["scheduled_local_datetime"][:19] == "2026-09-15T18:30:00"
        assert entry["scheduled_utc_datetime"][:19] == "2026-09-15T18:30:00"

    def test_timezone_normalization_ist(self, auth_client, project, approved_preview):
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        assert resp.status_code == 200
        entry = resp.json()["data"]["entry"]
        assert entry["timezone"] == "Asia/Kolkata"
        assert "2026-09-15T13:00:00" in entry["scheduled_utc_datetime"]


@pytest.mark.django_db
class TestScheduleListAPI:
    def test_list_entries(self, auth_client, project, approved_preview):
        auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["entries"]) == 1

    def test_list_entries_empty(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["entries"]) == 0


@pytest.mark.django_db
class TestScheduleCalendarAPI:
    def test_calendar_shows_active_entries(self, auth_client, project, approved_preview):
        auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/calendar/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["calendar"]) == 1

    def test_calendar_excludes_cancelled(self, auth_client, project, approved_preview):
        gen = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        eid = gen.json()["data"]["entry"]["id"]
        auth_client.post(f"/api/projects/{project.id}/schedule/{eid}/cancel/", format="json")
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/calendar/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["calendar"]) == 0


@pytest.mark.django_db
class TestScheduleDetailAPI:
    def test_get_entry_detail(self, auth_client, project, approved_preview):
        gen = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        eid = gen.json()["data"]["entry"]["id"]
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/{eid}/")
        assert resp.status_code == 200
        assert resp.json()["data"]["entry"]["id"] == eid

    def test_get_entry_not_found(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/99999/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestScheduleRescheduleAPI:
    def test_reschedule_success(self, auth_client, project, approved_preview):
        gen = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        eid = gen.json()["data"]["entry"]["id"]
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/{eid}/reschedule/",
            data={"scheduled_local_datetime": "2026-09-20T20:00:00", "timezone": "America/New_York"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        entry = resp.json()["data"]["entry"]
        assert entry["status"] == "rescheduled"
        assert entry["version"] == 2
        assert entry["timezone"] == "America/New_York"

    def test_reschedule_cancelled_rejected(self, auth_client, project, approved_preview):
        gen = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        eid = gen.json()["data"]["entry"]["id"]
        auth_client.post(f"/api/projects/{project.id}/schedule/{eid}/cancel/", format="json")
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/{eid}/reschedule/",
            data={"scheduled_local_datetime": "2026-09-20T20:00:00"},
            format="json",
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestScheduleCancelAPI:
    def test_cancel_success(self, auth_client, project, approved_preview):
        gen = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        eid = gen.json()["data"]["entry"]["id"]
        resp = auth_client.post(
            f"/api/projects/{project.id}/schedule/{eid}/cancel/",
            data={"reason": "Changed plans"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["data"]["entry"]["status"] == "cancelled"
        assert resp.json()["data"]["entry"]["cancellation_reason"] == "Changed plans"

    def test_cancel_already_cancelled(self, auth_client, project, approved_preview):
        gen = auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        eid = gen.json()["data"]["entry"]["id"]
        auth_client.post(f"/api/projects/{project.id}/schedule/{eid}/cancel/", format="json")
        resp = auth_client.post(f"/api/projects/{project.id}/schedule/{eid}/cancel/", format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestScheduleBestTimeAPI:
    def test_best_time_youtube(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/best-time/?platform=YouTube")
        assert resp.status_code == 200
        suggestion = resp.json()["data"]["suggestion"]
        assert "YouTube" in suggestion["reasoning"]

    def test_best_time_no_platform(self, auth_client, project):
        resp = auth_client.get(f"/api/projects/{project.id}/schedule/best-time/")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestScheduleTeamIsolation:
    def test_cross_team_returns_404(self, outsider_client, auth_client, project, approved_preview):
        auth_client.post(
            f"/api/projects/{project.id}/schedule/create/",
            data={"platform": "YouTube", "scheduled_local_datetime": "2026-09-15T18:30:00", "timezone": "Asia/Kolkata"},
            format="json",
        )
        resp = outsider_client.get(f"/api/projects/{project.id}/schedule/")
        assert resp.status_code == 404
