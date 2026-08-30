# -*- coding: utf-8 -*-
"""Scene media AsyncJob executor (Phase 2F, Task 25).

Registers the ``SCENE_MEDIA_GENERATION`` executor with the frozen Phase 2A job
substrate (``apps.ai_orchestration.tasks.register_executor``). The handler is
invoked by the Phase 2A ``execute_job`` Celery task, which drives AsyncJob state
transitions and retries; this module only performs the generation and returns a
structured result dict to be stored on the job.

A module-level provider seam lets tests inject a deterministic provider while
production defaults to the offline fake provider (hermetic, no credentials).
The real-provider branch is intentionally NOT exercised in this environment
(see runtime verification report).
"""
from apps.ai_orchestration.tasks import register_executor

from .providers.fake import FakeSceneMediaProvider

# Test seam: tests may override to inject a deterministic provider.
_provider = FakeSceneMediaProvider()


def set_provider(provider):
    """Test seam: set the provider used by the executor handler."""
    global _provider
    _provider = provider


def get_provider():
    """Return the active provider (module-level seam, overridable in tests)."""
    return _provider


def run_scene_media_generation(job):
    """Executor handler: generate + persist scene media for an approved package.

    Called by the Phase 2A ``execute_job`` task (pending -> running ->
    completed/failed). Returns a structured result dict stored on ``job.result``
    on success; raises on failure so ``execute_job`` marks the job failed.
    """
    from . import services

    return services.run_generation(job, provider=get_provider())


def register():
    """Register this executor with the frozen Phase 2A substrate (once)."""
    register_executor("scene_media_generation", run_scene_media_generation)
