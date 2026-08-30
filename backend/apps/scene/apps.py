# -*- coding: utf-8 -*-
from django.apps import AppConfig


class SceneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scene"
    verbose_name = "Scene Builder"

    def ready(self):
        # Phase 2E is synchronous and deterministic: the Scene Builder maps
        # already-approved artifacts and does not register a Phase 2A executor.
        # No registration is required here.
        pass
