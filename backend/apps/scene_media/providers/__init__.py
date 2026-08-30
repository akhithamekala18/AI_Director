# -*- coding: utf-8 -*-
"""Scene media provider registry (Phase 2F, Task 25).

Provider selection follows the frozen Phase 2A pattern (a name from settings, a
class registry). The default is the deterministic fake provider so the system is
fully usable offline and in tests without any external credential. Real
providers registers here can be selected via the ``SCENE_MEDIA_PROVIDER``
setting.
"""
from django.conf import settings

from .base import SceneMediaProvider, SceneMediaProviderError  # noqa: F401
from .fake import FakeSceneMediaProvider


class MediaProviderRegistry:
    """Registry of scene media provider classes, keyed by name."""

    _providers = {
        "fake": FakeSceneMediaProvider,
    }

    @classmethod
    def get_provider(cls, name=None) -> SceneMediaProvider:
        name = name or getattr(settings, "SCENE_MEDIA_PROVIDER", "fake")
        provider_class = cls._providers.get(name)
        if not provider_class:
            raise SceneMediaProviderError(f"Unknown scene media provider: {name}")
        return provider_class()

    @classmethod
    def register(cls, name, provider_class):
        cls._providers[name] = provider_class
