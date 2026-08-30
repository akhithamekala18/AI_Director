# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ScriptConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.script"
    verbose_name = "Script Generation"

    def ready(self):
        # Importing .tasks registers the script_generation executor with the
        # Phase 2A JOB_EXECUTORS registry (idempotent).
        from . import tasks  # noqa: F401
