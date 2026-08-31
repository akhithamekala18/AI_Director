# -*- coding: utf-8 -*-
"""Video generation engine (Task 36 / Overview section 20.1.7).

The engine composites approved scene media assets into a single video
output. Per-scene re-render is supported: regenerating a single scene
produces a new version with only that scene's assets changed (G-4).
"""


def composite_video(provider, scenes, platform_target="YouTube"):
    """Composite scenes into a video using the given provider.

    Args:
        provider: Video provider (fake or real) implementing composite().
        scenes: List of scene data dicts from the approved Scene Builder.
        platform_target: Target platform for aspect ratio/format.

    Returns:
        dict with asset_ref, duration_seconds, provider, provider_metadata.
    """
    if not scenes:
        raise ValueError("No scenes to composite")

    return provider.composite(scenes, platform_target)
