# -*- coding: utf-8 -*-
"""Thumbnail generation engine (Task 36 / Overview section 20.1.11).

The engine generates thumbnails from approved scene media assets.
"""


def generate_thumbnail(provider, scenes, title_text="", platform_target="YouTube"):
    """Generate a thumbnail using the given provider.

    Args:
        provider: Thumbnail provider (fake or real) implementing generate().
        scenes: List of scene data dicts from the approved Scene Builder.
        title_text: Title text to overlay on the thumbnail.
        platform_target: Target platform for dimensions.

    Returns:
        dict with asset_ref, variations, provider, provider_metadata.
    """
    if not scenes:
        raise ValueError("No scenes available for thumbnail generation")

    return provider.generate(scenes, title_text, platform_target)
