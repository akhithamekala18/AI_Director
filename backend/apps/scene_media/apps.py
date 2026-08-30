# -*- coding: utf-8 -*-
from django.apps import AppConfig


class SceneMediaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scene_media"
    verbose_name = "Scene Media"

    def ready(self):
        # Register the SCENE_MEDIA_GENERATION executor with the frozen Phase 2A
        # AsyncJob substrate so the Phase 2A task can execute media generation.
        from . import tasks

        tasks.register()
