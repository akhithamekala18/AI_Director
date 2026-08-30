# -*- coding: utf-8 -*-
"""Provider selection for regeneration.

Regeneration reuses the frozen Phase 2F scene-media provider abstraction
(``apps.scene_media.providers``) — the same provider interface that produced the
original media. Regeneration therefore chooses its provider through that
registry so regenerated assets match the original generation contract. The
default is the deterministic fake provider (hermetic, offline, no credentials).
"""
from apps.scene_media.providers.fake import FakeSceneMediaProvider  # noqa: F401
