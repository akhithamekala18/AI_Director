# -*- coding: utf-8 -*-
"""Regeneration AsyncJob executor (Phase 2G, Task 26).

Registers the ``REGENERATION`` executor with the frozen Phase 2A job substrate
(``apps.ai_orchestration.tasks.register_executor``). The handler is invoked by
the Phase 2A ``execute_job`` Celery task, which drives AsyncJob state transitions
and retries; this module only performs the regeneration and returns a structured
result dict to be stored on the job.

A module-level provider seam lets tests inject a deterministic provider while
production defaults to the offline fake provider (hermetic, no credentials).
Real external providers are intentionally NOT exercised in this environment
(see runtime verification report).
"""
from apps.ai_orchestration.tasks import register_executor
from apps.scene_media.providers.fake import FakeSceneMediaProvider

# Test seam: tests may override to inject a deterministic provider.
_provider = FakeSceneMediaProvider()


def set_provider(provider):
    """Test seam: set the provider used by the executor handler."""
    global _provider
    _provider = provider


def get_provider():
    """Return the active provider (module-level seam, overridable in tests)."""
    return _provider


def run_regeneration_executor(job):
    """Executor handler: snapshot + regenerate targeted scenes' media only.

    Called by the Phase 2A ``execute_job`` task (pending -> running ->
    completed/failed). Returns a structured result dict stored on ``job.result``
    on success; raises on failure so ``execute_job`` marks the job failed and no
    false success is produced.
    """
    from . import services

    return services.run_regeneration(job, provider=get_provider())


def register():
    """Register this executor with the frozen Phase 2A substrate (once)."""
    register_executor("regeneration", run_regeneration_executor)
