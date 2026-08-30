# -*- coding: utf-8 -*-
"""AI orchestration services (Development Plan Day 20).

Provides the AI service layer that business logic uses to interact with
AI providers through the adapter abstraction.
"""
import logging
from decimal import Decimal

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from .models import AsyncJob
from .providers.base import AIProviderError
from .providers.registry import ProviderRegistry

logger = logging.getLogger("apps.ai_orchestration")


def create_job(user, project, job_type, metadata=None):
    """Create a new async job.

    Args:
        user: The user creating the job.
        project: The project this job belongs to.
        job_type: Type of job (from AsyncJob.JobType).
        metadata: Optional job-specific metadata.

    Returns:
        Created AsyncJob instance.
    """
    # A job always belongs to the same team as its project. The view already
    # authorised this user for the project (membership in project.team), so
    # binding the job to project.team keeps job.team == project.team invariant.
    team = project.team
    job = AsyncJob.objects.create(
        team=team,
        project=project,
        owner=user,
        job_type=job_type,
        metadata=metadata or {},
    )
    record_audit(
        user,
        AuditAction.CREATE.value,
        "job",
        job.id,
        f"created {job_type} job",
    )
    return job


def get_job(user, job_id):
    """Get a job by ID with team isolation.

    Args:
        user: The user requesting the job.
        job_id: The job ID.

    Returns:
        AsyncJob if found and accessible, None otherwise.
    """
    team_ids = user.memberships.values_list("team_id", flat=True)
    return AsyncJob.objects.filter(id=job_id, team_id__in=team_ids).first()


def list_jobs_for_project(user, project):
    """List jobs for a project with team isolation.

    Args:
        user: The user requesting jobs.
        project: The project to list jobs for.

    Returns:
        QuerySet of AsyncJob instances.
    """
    team_ids = user.memberships.values_list("team_id", flat=True)
    return AsyncJob.objects.filter(project=project, team_id__in=team_ids)


def cancel_job(user, job):
    """Cancel a pending or running job.

    Args:
        user: The user requesting cancellation.
        job: The job to cancel.

    Raises:
        ValueError: If job cannot be cancelled.
    """
    if not job.can_transition(AsyncJob.Status.CANCELLED):
        raise ValueError(f"Job cannot be cancelled from status: {job.status}")

    job.transition_to(AsyncJob.Status.CANCELLED)
    job.save(update_fields=["status", "updated_at"])
    record_audit(
        user,
        AuditAction.UPDATE.value,
        "job",
        job.id,
        "cancelled job",
    )


def retry_job(user, job):
    """Retry a failed job.

    Args:
        user: The user requesting retry.
        job: The job to retry.

    Raises:
        ValueError: If job cannot be retried.
    """
    if not job.can_transition(AsyncJob.Status.RETRYING):
        raise ValueError(f"Job cannot be retried from status: {job.status}")

    if job.retry_count >= job.max_retries:
        raise ValueError("Maximum retries exceeded")

    job.transition_to(AsyncJob.Status.RETRYING)
    job.error_message = ""
    job.retry_count += 1
    job.save(
        update_fields=["status", "error_message", "retry_count", "updated_at"]
    )
    record_audit(
        user,
        AuditAction.UPDATE.value,
        "job",
        job.id,
        "retried job",
    )


def get_provider(name=None):
    """Get an AI provider adapter.

    Args:
        name: Optional provider name. Defaults to configured provider.

    Returns:
        AIProviderAdapter instance.
    """
    return ProviderRegistry.get_provider(name)
