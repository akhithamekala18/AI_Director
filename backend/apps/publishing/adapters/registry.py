# -*- coding: utf-8 -*-
"""Adapter registry for platform publishing (DG-11)."""
from .base import PlatformAdapter

_registry: dict[str, type[PlatformAdapter]] = {}


def register_adapter(platform: str, adapter_class: type[PlatformAdapter]):
    """Register a platform adapter."""
    _registry[platform] = adapter_class


def get_adapter(platform: str) -> PlatformAdapter:
    """Get an adapter instance for a platform."""
    cls = _registry.get(platform)
    if cls is None:
        raise ValueError(f"No adapter registered for platform: {platform}")
    return cls()
