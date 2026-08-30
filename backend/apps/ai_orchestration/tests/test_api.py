# -*- coding: utf-8 -*-
"""Tests for AI orchestration API endpoints."""
import pytest

from apps.ai_orchestration.models import AsyncJob
from apps.projects.models import Project


@pytest.mark.django_db
class TestJobAPI:
    """Test job API endpoints."""

    def test_create_job(self, api_client):
        """POST /api/orchestration/jobs/ creates a job."""
        client = api_client()
        user = client.user
        team = user.memberships.first().team
        project = Project.objects.create(
            team=team, owner=user, topic="API Test Project"
        )

        response = client.post(
            "/api/orchestration/jobs/",
            {
                "project_id": project.id,
                "job_type": "research_generation",
                "metadata": {"topic": "test"},
            },
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job"]["job_type"] == "research_generation"
        assert data["data"]["job"]["status"] == "pending"

    def test_list_jobs(self, api_client):
        """GET /api/orchestration/jobs/ lists jobs."""
        client = api_client()
        user = client.user
        team = user.memberships.first().team
        project = Project.objects.create(
            team=team, owner=user, topic="List Test Project"
        )

        AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        response = client.get(
            f"/api/orchestration/jobs/?project_id={project.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["jobs"]) == 1

    def test_get_job_detail(self, api_client):
        """GET /api/orchestration/jobs/{id}/ returns job details."""
        client = api_client()
        user = client.user
        team = user.memberships.first().team
        project = Project.objects.create(
            team=team, owner=user, topic="Detail Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        response = client.get(f"/api/orchestration/jobs/{job.id}/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job"]["id"] == job.id

    def test_cancel_job(self, api_client):
        """POST /api/orchestration/jobs/{id}/cancel/ cancels a job."""
        client = api_client()
        user = client.user
        team = user.memberships.first().team
        project = Project.objects.create(
            team=team, owner=user, topic="Cancel Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        response = client.post(f"/api/orchestration/jobs/{job.id}/cancel/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job"]["status"] == "cancelled"

    def test_retry_job(self, api_client):
        """POST /api/orchestration/jobs/{id}/retry/ retries a failed job."""
        client = api_client()
        user = client.user
        team = user.memberships.first().team
        project = Project.objects.create(
            team=team, owner=user, topic="Retry Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.FAILED,
            retry_count=0,
        )

        response = client.post(f"/api/orchestration/jobs/{job.id}/retry/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["job"]["status"] == "retrying"

    def test_team_isolation(self, api_client, make_user):
        """User cannot access other team's job."""
        client = api_client()
        user_a = client.user
        team_a = user_a.memberships.first().team
        project_a = Project.objects.create(
            team=team_a, owner=user_a, topic="Team A Project"
        )

        user_b = make_user(username="other_team_user")
        team_b = user_b.memberships.first().team
        project_b = Project.objects.create(
            team=team_b, owner=user_b, topic="Team B Project"
        )

        job_b = AsyncJob.objects.create(
            team=team_b,
            project=project_b,
            owner=user_b,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        # User A tries to access User B's job
        response = client.get(f"/api/orchestration/jobs/{job_b.id}/")
        assert response.status_code == 404

    def test_unauthenticated_access(self, make_user):
        """Unauthenticated user cannot access jobs."""
        from rest_framework.test import APIClient
        client = APIClient()

        response = client.get("/api/orchestration/jobs/")
        # Note: DRF returns 403 for unauthenticated by default (pre-existing pattern)
        assert response.status_code in (401, 403)

    def test_cross_team_cancel_rejected(self, api_client, make_user):
        """User A cannot cancel Team B's job (404 through team-scoped get_job)."""
        client = api_client()

        user_b = make_user(username="other_team_b")
        team_b = user_b.memberships.first().team
        from apps.projects.models import Project
        project_b = Project.objects.create(team=team_b, owner=user_b, topic="PB")
        job_b = AsyncJob.objects.create(
            team=team_b, project=project_b, owner=user_b,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        response = client.post(f"/api/orchestration/jobs/{job_b.id}/cancel/")
        assert response.status_code == 404

    def test_cross_team_retry_rejected(self, api_client, make_user):
        """User A cannot retry Team B's job (404 through team-scoped get_job)."""
        client = api_client()

        user_b = make_user(username="other_team_retry")
        team_b = user_b.memberships.first().team
        from apps.projects.models import Project
        project_b = Project.objects.create(team=team_b, owner=user_b, topic="PB")
        job_b = AsyncJob.objects.create(
            team=team_b, project=project_b, owner=user_b,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.FAILED,
        )

        response = client.post(f"/api/orchestration/jobs/{job_b.id}/retry/")
        assert response.status_code == 404

    def test_cross_team_create_rejected(self, api_client, make_user):
        """User A cannot create a job on Team B's project (404)."""
        client = api_client()

        user_b = make_user(username="other_team_create")
        team_b = user_b.memberships.first().team
        from apps.projects.models import Project
        project_b = Project.objects.create(team=team_b, owner=user_b, topic="PB")

        response = client.post(
            "/api/orchestration/jobs/",
            {"project_id": project_b.id, "job_type": "research_generation"},
            format="json",
        )
        assert response.status_code == 404
        assert AsyncJob.objects.filter(project=project_b).count() == 0
