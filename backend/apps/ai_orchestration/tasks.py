# -*- coding: utf-8 -*-
"""Celery task definitions for AI job execution (DG-8; Phase 2A F10).

Provides the minimal task substrate that drives an AsyncJob through its state
machine inside a Celery worker while preserving team ownership and audit.

Concrete per-job-type executors (research, script, character, scene, media,
regeneration) are provided by later phases (2B-2G). Until a handler is
registered for a job type, the job fails deterministically with a clear error
rather than silently succeeding.
"""
import logging

from celery import shared_task
from django.utils import timezone

from apps.audit.services import record_audit
from apps.core.enums import AuditAction

from .models import AsyncJob

logger = logging.getLogger("apps.ai_orchestration")

# Registered per-job-type executors. Handlers raised by later phases register
# here via register_executor(). The Phase 2A substrate ships with none so that
# no speculative engine logic is introduced before its owning phase.
JOB_EXECUTORS = {}


def register_executor(job_type, handler):
    """Register a callable that runs a job of `job_type`.

    The handler is invoked as handler(job) and returns a dict to store in
    `job.result` on success (may also update `job.progress`/`job.metadata`).
    """
    JOB_EXECUTORS[job_type] = handler


def _does_not_exist(job_id):
    """Return a small dict when a job id does not resolve (graceful degrade)."""
    return {"job_id": job_id, "status": "unknown"}


@shared_task(bind=True, queue="default")
def execute_job(self, job_id):
    """Execute an AsyncJob inside a Celery worker.

    Drives the job through valid state transitions: pending -> running ->
    completed (on success) or -> failed (on error). Running a job that is not
    in a startable state is a controlled no-op (returns current status).

    Args:
        job_id: The AsyncJob primary key.

    Returns:
        dict describing the terminal job state.
    """
    job = AsyncJob.objects.filter(id=job_id).first()
    if job is None:
        logger.warning("execute_job: job %s not found", job_id)
        return _does_not_exist(job_id)

    if not job.can_transition(AsyncJob.Status.RUNNING):
        logger.warning("execute_job: job %s cannot start from %r", job.id, job.status)
        return {"job_id": job.id, "status": job.status, "started": False}

    job.transition_to(AsyncJob.Status.RUNNING)
    job.started_at = timezone.now()
    job.progress = 0.0
    job.save(update_fields=["status", "started_at", "progress", "updated_at"])
    record_audit(job.owner, AuditAction.UPDATE.value, "job", job.id, "job started")

    handler = JOB_EXECUTORS.get(job.job_type)
    if handler is None:
        message = (
            f"Job type {job.job_type!r} has no executor configured in Phase 2A"
        )
        _fail_job(job, message)
        return {"job_id": job.id, "status": job.status, "error": message}

    try:
        result = handler(job)
    except Exception as exc:  # noqa: BLE001 - worker must mark failed on any error
        logger.exception("execute_job: job %s failed", job.id)
        _fail_job(job, str(exc))
        return {"job_id": job.id, "status": job.status, "error": str(exc)}

    if not job.can_transition(AsyncJob.Status.COMPLETED):
        # A handler may already have moved the job (e.g. cancelled). Respect it.
        return {"job_id": job.id, "status": job.status}

    job.transition_to(AsyncJob.Status.COMPLETED)
    job.result = result or {}
    job.progress = 1.0
    job.completed_at = timezone.now()
    job.save(
        update_fields=["status", "result", "progress", "completed_at", "updated_at"]
    )
    record_audit(job.owner, AuditAction.UPDATE.value, "job", job.id, "job completed")
    return {"job_id": job.id, "status": job.status, "completed": True}


def _fail_job(job, message):
    """Transition a running job to failed with a persisted error message."""
    if not job.can_transition(AsyncJob.Status.FAILED):
        return
    job.transition_to(AsyncJob.Status.FAILED)
    job.error_message = (message or "")[:1000]
    job.save(update_fields=["status", "error_message", "updated_at"])
    record_audit(job.owner, AuditAction.UPDATE.value, "job", job.id, "job failed")
