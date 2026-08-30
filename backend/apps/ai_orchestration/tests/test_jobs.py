# -*- coding: utf-8 -*-
"""Tests for AsyncJob model and job services."""
import pytest

from apps.ai_orchestration.models import AsyncJob
from apps.ai_orchestration.services import (
    cancel_job,
    create_job,
    get_job,
    list_jobs_for_project,
    retry_job,
)


@pytest.mark.django_db
class TestAsyncJobModel:
    """Test AsyncJob model."""

    def test_create_job(self, make_user):
        """Job creation with team isolation."""
        user = make_user(username="jobcreator")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            metadata={"topic": "AI Director"},
        )

        assert job.status == AsyncJob.Status.PENDING
        assert job.progress == 0.0
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert job.cost == 0
        assert job.metadata == {"topic": "AI Director"}

    def test_valid_transition(self, make_user):
        """Valid state transitions succeed."""
        user = make_user(username="transition_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        # pending -> running
        assert job.can_transition(AsyncJob.Status.RUNNING)
        job.transition_to(AsyncJob.Status.RUNNING)
        assert job.status == AsyncJob.Status.RUNNING

        # running -> completed
        assert job.can_transition(AsyncJob.Status.COMPLETED)
        job.transition_to(AsyncJob.Status.COMPLETED)
        assert job.status == AsyncJob.Status.COMPLETED

    def test_invalid_transition(self, make_user):
        """Invalid state transitions raise ValueError."""
        user = make_user(username="invalid_transition")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        # pending -> completed (invalid)
        assert not job.can_transition(AsyncJob.Status.COMPLETED)
        with pytest.raises(ValueError):
            job.transition_to(AsyncJob.Status.COMPLETED)

    def test_terminal_states(self, make_user):
        """Completed and cancelled are terminal states."""
        user = make_user(username="terminal_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        # Completed job
        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.COMPLETED,
        )
        assert not job.can_transition(AsyncJob.Status.RUNNING)

        # Cancelled job
        job2 = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.CANCELLED,
        )
        assert not job2.can_transition(AsyncJob.Status.RUNNING)

    def test_retry_flow(self, make_user):
        """Failed job can be retried."""
        user = make_user(username="retry_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.FAILED,
            retry_count=0,
        )

        # failed -> retrying
        assert job.can_transition(AsyncJob.Status.RETRYING)
        job.transition_to(AsyncJob.Status.RETRYING)
        assert job.status == AsyncJob.Status.RETRYING

        # retrying -> running
        assert job.can_transition(AsyncJob.Status.RUNNING)
        job.transition_to(AsyncJob.Status.RUNNING)
        assert job.status == AsyncJob.Status.RUNNING


@pytest.mark.django_db
class TestJobServices:
    """Test job service functions."""

    def test_create_job_service(self, make_user):
        """Service creates job with audit."""
        user = make_user(username="svc_creator")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = create_job(
            user=user,
            project=project,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            metadata={"topic": "test"},
        )

        assert job.id is not None
        assert job.team == team
        assert job.project == project
        assert job.owner == user
        assert job.status == AsyncJob.Status.PENDING

    def test_get_job_team_isolation(self, make_user):
        """User cannot access other team's job."""
        user_a = make_user(username="user_a_isolation")
        user_b = make_user(username="user_b_isolation")

        team_a = user_a.memberships.first().team
        from apps.projects.models import Project
        project_a = Project.objects.create(
            team=team_a, owner=user_a, topic="Project A"
        )

        job = AsyncJob.objects.create(
            team=team_a,
            project=project_a,
            owner=user_a,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        # User A can access
        found = get_job(user_a, job.id)
        assert found is not None

        # User B cannot access (different team)
        found_b = get_job(user_b, job.id)
        assert found_b is None

    def test_cancel_job_service(self, make_user):
        """Service cancels job."""
        user = make_user(username="cancel_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )

        cancel_job(user, job)
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.CANCELLED

    def test_retry_job_service(self, make_user):
        """Service retries failed job."""
        user = make_user(username="retry_svc_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.FAILED,
            retry_count=0,
        )

        retry_job(user, job)
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.RETRYING

    def test_retry_max_exceeded(self, make_user):
        """Cannot retry when max retries exceeded."""
        user = make_user(username="max_retry_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        job = AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.FAILED,
            retry_count=3,
            max_retries=3,
        )

        with pytest.raises(ValueError, match="Maximum retries"):
            retry_job(user, job)

    def test_list_jobs_for_project(self, make_user):
        """List jobs for a project."""
        user = make_user(username="list_user")
        team = user.memberships.first().team
        from apps.projects.models import Project
        project = Project.objects.create(
            team=team, owner=user, topic="Test Project"
        )

        AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )
        AsyncJob.objects.create(
            team=team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.SCRIPT_GENERATION,
        )

        jobs = list_jobs_for_project(user, project)
        assert jobs.count() == 2


@pytest.mark.django_db
class TestRetryCount:
    """DEFECT 1: retry_count must increment exactly once per retry and persist."""

    def _failed_job(self, user, project):
        return AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.FAILED,
            retry_count=0,
        )

    def test_first_retry_increments_to_one(self, make_user):
        user = make_user(username="rc_user")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._failed_job(user, project)
        retry_job(user, job)
        job.refresh_from_db()
        assert job.retry_count == 1

    def test_second_retry_increments_to_two(self, make_user):
        user = make_user(username="rc_user2")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._failed_job(user, project)
        retry_job(user, job)  # -> retrying (count 1)
        # back to failed so it can be retried again
        job.status = AsyncJob.Status.FAILED
        job.save(update_fields=["status"])
        retry_job(user, job)  # -> retrying (count 2)
        job.refresh_from_db()
        assert job.retry_count == 2

    def test_retry_count_persists_after_reload(self, make_user):
        user = make_user(username="rc_user3")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._failed_job(user, project)
        retry_job(user, job)
        # reload from a fresh query to simulate a new request/transaction
        fresh = AsyncJob.objects.get(id=job.id)
        assert fresh.retry_count == 1

    def test_repeated_retries_respect_max_retries(self, make_user):
        user = make_user(username="rc_user4")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._failed_job(user, project)  # max_retries=3
        count = 0
        for _ in range(10):
            job.refresh_from_db()
            if job.status == AsyncJob.Status.RETRYING:
                job.status = AsyncJob.Status.FAILED
                job.save(update_fields=["status"])
            try:
                retry_job(user, job)
                count += 1
            except ValueError as exc:
                assert "Maximum retries" in str(exc)
                break
        assert count == 3
        job.refresh_from_db()
        assert job.retry_count == 3

    def test_retry_does_not_create_duplicate_jobs(self, make_user):
        user = make_user(username="rc_user5")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = self._failed_job(user, project)
        before = AsyncJob.objects.count()
        retry_job(user, job)
        assert AsyncJob.objects.count() == before  # no duplicate rows

    def test_retry_rejected_from_invalid_state(self, make_user):
        user = make_user(username="rc_user6")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = AsyncJob.objects.create(
            team=project.team,
            project=project,
            owner=user,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
            status=AsyncJob.Status.PENDING,
        )
        with pytest.raises(ValueError, match="cannot be retried"):
            retry_job(user, job)
        job.refresh_from_db()
        assert job.status == AsyncJob.Status.PENDING  # state not mutated


@pytest.mark.django_db
class TestTeamProjectInvariant:
    """DEFECT 2: job.team == project.team and membership-scoped access."""

    def test_job_belongs_to_projects_team(self, make_user):
        user = make_user(username="invariant_user")
        from apps.projects.models import Project
        project = Project.objects.create(
            team=user.memberships.first().team, owner=user, topic="P"
        )
        job = create_job(
            user=user,
            project=project,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )
        assert job.team_id == project.team_id

    def test_multiple_memberships_resolve_secondary_team(self, make_user):
        """A user with memberships in two teams can access jobs of both."""
        from apps.accounts.models import Team
        from apps.projects.models import Project

        user_a = make_user(username="multi_a")
        # second team + membership for user_a
        team_b = Team.objects.create(name="Team B for multi_a")
        user_a.memberships.create(team=team_b, role="Creator")

        # Project owned in team B (secondary for user_a)
        project_b = Project.objects.create(team=team_b, owner=user_a, topic="PB")
        job_b = create_job(
            user=user_a, project=project_b,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )
        # user_a must see the job (they're a member of team B)
        assert get_job(user_a, job_b.id) is not None
        assert list_jobs_for_project(user_a, project_b).count() == 1

    def test_cross_team_job_access_rejected(self, make_user):
        user_a = make_user(username="iso_a")
        user_b = make_user(username="iso_b")
        team_a = user_a.memberships.first().team
        from apps.projects.models import Project
        project_a = Project.objects.create(team=team_a, owner=user_a, topic="PA")
        job_a = create_job(
            user=user_a, project=project_a,
            job_type=AsyncJob.JobType.RESEARCH_GENERATION,
        )
        # user_b is not a member of team_a -> cannot resolve the job (the view
        # uses get_job() to return 404 for detail/cancel/retry).
        assert get_job(user_b, job_a.id) is None
        assert list_jobs_for_project(user_b, project_a).count() == 0
        # The view layer rejects cross-team cancel/retry because get_object()
        # returns None (NotFound); verified at the API level in test_api.py.

    def test_cross_team_project_access_rejected(self, make_user):
        user_a = make_user(username="proj_a")
        user_b = make_user(username="proj_b")
        team_a = user_a.memberships.first().team
        from apps.projects.models import Project
        from apps.projects.services import get_project
        Project.objects.create(team=team_a, owner=user_a, topic="PA")
        projects_b = list(Project.objects.filter(team=team_a))
        # user_b belongs only to their own team, so cannot resolve the project
        assert get_project(user_b, projects_b[0].id) is None
