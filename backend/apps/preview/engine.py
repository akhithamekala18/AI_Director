# -*- coding: utf-8 -*-
"""Preview rendering engine (Task 37).

Delegates to a provider to render a platform-accurate preview of a video.
"""
from .providers.fake import FakePreviewProvider


def render_preview(provider, video_asset, platform_target):
    """Render a platform-accurate preview via the given provider.

    Args:
        provider: A preview provider instance (e.g. FakePreviewProvider).
        video_asset: The VideoAsset to preview.
        platform_target: The target platform for the preview.

    Returns:
        dict with asset_ref, provider, provider_metadata, duration_seconds,
        width, height.
    """
    return provider.render_preview(video_asset, platform_target)
