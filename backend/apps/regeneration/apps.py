# -*- coding: utf-8 -*-
from django.apps import AppConfig


class RegenerationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.regeneration"
    verbose_name = "Regeneration / Editing"

    def ready(self):
        # Register the REGENERATION executor with the frozen Phase 2A AsyncJob
        # substrate so the Phase 2A task can execute scene regeneration.
        from . import tasks

        tasks.register()
