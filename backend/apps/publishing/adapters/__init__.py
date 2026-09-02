# -*- coding: utf-8 -*-
"""Platform publishing adapters (DG-11).

Registers all platform adapters on import.
"""
from .registry import get_adapter, register_adapter  # noqa: F401
from .base import PlatformAdapter, PublishResult, TokenData, AccountInfo  # noqa: F401
from .youtube import YouTubeAdapter  # noqa: F401
from .instagram import InstagramAdapter  # noqa: F401
from .tiktok import TikTokAdapter  # noqa: F401

# Register all adapters
register_adapter("YouTube", YouTubeAdapter)
register_adapter("Instagram", InstagramAdapter)
register_adapter("TikTok", TikTokAdapter)
