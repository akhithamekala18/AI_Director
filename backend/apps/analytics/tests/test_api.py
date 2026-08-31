# -*- coding: utf-8 -*-
import pytest
from rest_framework.test import APIClient

from apps.analytics import services
from apps.analytics.models import PublishedPerformance


class TestRecordPublishedPerformance:
    """Test the analytics boundary: only published entries are tracked."""

    def test_record_for_published_entry(self, published_entry):
        obj = services.record_published_performance(
            published_entry, views=100, likes=20, comments=5, shares=3,
            topic="test-topic"
        )
        assert obj.views == 100
        assert obj.likes == 20
        assert obj.comments == 5
        assert obj.shares == 3
        assert obj.topic == "test-topic"
        assert obj.platform == "YouTube"
        assert obj.engagement_rate > 0

    def test_record_rejects_unpublished_entry(self, unpublished_entry):
        with pytest.raises(ValueError, match="analytics only tracks published"):
            services.record_published_performance(
                unpublished_entry, views=50, likes=10
            )

    def test_engagement_rate_zero_views(self, published_entry):
        obj = services.record_published_performance(
            published_entry, views=0, likes=5, comments=1, shares=0
        )
        assert obj.engagement_rate == 0.0

    def test_update_existing_record(self, published_entry):
        services.record_published_performance(
            published_entry, views=100, likes=10
        )
        obj = services.record_published_performance(
            published_entry, views=200, likes=20
        )
        assert obj.views == 200
        assert obj.likes == 20
        assert PublishedPerformance.objects.filter(entry=published_entry).count() == 1


class TestAnalyticsSummary:
    """Test aggregated analytics summary."""

    def test_summary_empty(self, auth_client, team):
        resp = auth_client.get("/api/analytics/summary/", {"team_id": team.id})
        assert resp.status_code == 200
        assert resp.data["data"]["summary"]["total_views"] is None

    def test_summary_with_data(self, auth_client, published_entry, team):
        services.record_published_performance(
            published_entry, views=100, likes=10, comments=5, shares=2
        )
        resp = auth_client.get("/api/analytics/summary/", {"team_id": team.id})
        assert resp.status_code == 200
        summary = resp.data["data"]["summary"]
        assert summary["total_views"] == 100
        assert summary["total_likes"] == 10

    def test_summary_team_isolation(self, auth_client, outsider_client, published_entry, team):
        services.record_published_performance(
            published_entry, views=100, likes=10
        )
        resp = auth_client.get("/api/analytics/summary/", {"team_id": team.id})
        assert resp.status_code == 200
        assert resp.data["data"]["summary"]["total_views"] == 100
        # outsider should not see this data
        resp2 = outsider_client.get("/api/analytics/summary/", {"team_id": team.id})
        assert resp2.status_code == 200
        assert resp2.data["data"]["summary"]["total_views"] is None


class TestAnalyticsByPlatform:
    """Test analytics grouped by platform."""

    def test_by_platform(self, auth_client, published_entry, team):
        services.record_published_performance(
            published_entry, views=50, likes=5
        )
        resp = auth_client.get("/api/analytics/by-platform/", {"team_id": team.id})
        assert resp.status_code == 200
        platforms = resp.data["data"]["platforms"]
        assert len(platforms) >= 1
        assert platforms[0]["platform"] == "YouTube"


class TestAnalyticsByTopic:
    """Test analytics grouped by topic."""

    def test_by_topic(self, auth_client, published_entry, team):
        services.record_published_performance(
            published_entry, views=75, likes=8, topic="tutorial"
        )
        resp = auth_client.get("/api/analytics/by-topic/", {"team_id": team.id})
        assert resp.status_code == 200
        topics = resp.data["data"]["topics"]
        assert len(topics) >= 1
        assert topics[0]["topic"] == "tutorial"


class TestAuditExport:
    """Test audit export functionality."""

    def test_export_csv(self, auth_client):
        resp = auth_client.post("/api/analytics/audit-export/", {"format": "csv"})
        assert resp.status_code == 200
        assert "export" in resp.data["data"]

    def test_export_json(self, auth_client):
        resp = auth_client.post("/api/analytics/audit-export/", {"format": "json"})
        assert resp.status_code == 200

    def test_export_invalid_format(self, auth_client):
        resp = auth_client.post("/api/analytics/audit-export/", {"format": "xml"})
        assert resp.status_code == 400


class TestAnalyticsRecordAPI:
    """Test the record endpoint."""

    def test_record_api(self, auth_client, published_entry):
        resp = auth_client.post("/api/analytics/record/", {
            "entry_id": published_entry.id,
            "views": 200, "likes": 30, "comments": 10, "shares": 5,
            "topic": "api-test",
        }, format="json")
        assert resp.status_code == 200
        assert "analytics" in resp.data["data"]

    def test_record_missing_entry(self, auth_client):
        resp = auth_client.post("/api/analytics/record/", {
            "entry_id": 99999,
            "views": 100,
        }, format="json")
        assert resp.status_code == 404

    def test_record_unpublished_entry(self, auth_client, unpublished_entry):
        resp = auth_client.post("/api/analytics/record/", {
            "entry_id": unpublished_entry.id,
            "views": 100,
        }, format="json")
        assert resp.status_code == 400

    def test_record_unauthenticated(self, published_entry):
        client = APIClient()
        resp = client.post("/api/analytics/record/", {
            "entry_id": published_entry.id,
            "views": 100,
        }, format="json")
        assert resp.status_code in (401, 403)


class TestBoundaryInvariant:
    """Analytics boundary: only published entries are measured."""

    def test_scheduled_entry_rejected(self, auth_client, unpublished_entry):
        resp = auth_client.post("/api/analytics/record/", {
            "entry_id": unpublished_entry.id,
            "views": 100,
        }, format="json")
        assert resp.status_code == 400

    def test_published_entry_accepted(self, auth_client, published_entry):
        resp = auth_client.post("/api/analytics/record/", {
            "entry_id": published_entry.id,
            "views": 100,
        }, format="json")
        assert resp.status_code == 200
