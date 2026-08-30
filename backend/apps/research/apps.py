# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ResearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.research"
    verbose_name = "Research Engine"

    def ready(self):
        # Importing .tasks registers the research_generation executor with the
        # Phase 2A JOB_EXECUTORS registry (idempotent).
        from . import tasks  # noqa: F401
