# -*- coding: utf-8 -*-
"""Base class for platform publishing adapters (DG-11).

All platform adapters must inherit from this class and implement
the abstract methods. The application layer depends only on this
interface, never on platform-specific HTTP logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PublishResult:
    """Normalized result from a platform publish operation."""
    success: bool
    platform: str
    platform_post_id: str = ""
    published_url: str = ""
    published_at: str = ""
    error_code: str = ""
    error_message: str = ""
    retryable: bool = False
    provider_metadata: dict = field(default_factory=dict)


@dataclass
class TokenData:
    """Normalized OAuth token data."""
    access_token: str
    refresh_token: str = ""
    expires_in: int = 0
    token_type: str = "Bearer"
    scope: str = ""
    provider_metadata: dict = field(default_factory=dict)


@dataclass
class AccountInfo:
    """Normalized platform account information."""
    platform: str
    platform_account_id: str
    display_name: str
    provider_metadata: dict = field(default_factory=dict)


class PlatformAdapter(ABC):
    """Abstract base class for platform publishing adapters."""

    platform: str = ""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Return the OAuth authorization URL for this platform."""

    @abstractmethod
    def exchange_code(self, code: str) -> TokenData:
        """Exchange an authorization code for tokens."""

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> TokenData:
        """Refresh an expired access token."""

    @abstractmethod
    def get_account_info(self, access_token: str) -> AccountInfo:
        """Fetch the authenticated user's account information."""

    @abstractmethod
    def upload_media(self, access_token: str, file_path: str, metadata: dict) -> str:
        """Upload media to the platform. Returns platform media ID."""

    @abstractmethod
    def publish(self, access_token: str, media_id: str, metadata: dict) -> PublishResult:
        """Publish/uploaded media. Returns publish result."""

    @abstractmethod
    def normalize_error(self, exc: Exception) -> PublishResult:
        """Normalize platform-specific errors into a PublishResult."""
