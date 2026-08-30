# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CharacterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.character"
    verbose_name = "Character Library"

    def ready(self):
        # Importing .tasks registers the character_detection executor with the
        # Phase 2A JOB_EXECUTORS registry (idempotent).
        from . import tasks  # noqa: F401
