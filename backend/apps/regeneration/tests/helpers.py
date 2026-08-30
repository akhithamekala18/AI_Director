# -*- coding: utf-8 -*-
"""Shared helpers for regeneration tests."""
from apps.scene_media import services as media_services
from apps.scene_media.tests.helpers import approved_scene_builder, make_project  # noqa: F401


def setup_media(user, project, media_types=None):
    """Generate scene media for an approved project (Task 25)."""
    approved_scene_builder(user, project)
    job = media_services.request_scene_media(user, project, media_types=media_types)
    return job


def setup_media_full(user, project):
    """Generate all media types. Returns (job, media_count)."""
    job = setup_media(user, project)
    from apps.scene_media.models import SceneMedia
    count = SceneMedia.objects.filter(project=project).count()
    return job, count
