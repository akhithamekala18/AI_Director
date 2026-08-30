# -*- coding: utf-8 -*-
"""Provider-agnostic AI adapter interface (§41.2, §24.3).

Business logic must depend on this abstraction, never directly on
provider-specific HTTP implementations.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class AIProviderError(Exception):
    """Base exception for AI provider errors."""

    def __init__(self, message: str, status_code: int = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class AIProviderTimeoutError(AIProviderError):
    """Raised when an AI provider request times out."""

    def __init__(self, message: str = "AI provider request timed out"):
        super().__init__(message, retryable=True)


class AIProviderRateLimitError(AIProviderError):
    """Raised when rate limited by an AI provider."""

    def __init__(self, message: str = "AI provider rate limit exceeded"):
        super().__init__(message, status_code=429, retryable=True)


class AIProviderAuthError(AIProviderError):
    """Raised when authentication fails with an AI provider."""

    def __init__(self, message: str = "AI provider authentication failed"):
        super().__init__(message, status_code=401, retryable=False)


class AIProviderContentError(AIProviderError):
    """Raised when content policy is violated."""

    def __init__(self, message: str = "AI provider content policy violation"):
        super().__init__(message, status_code=400, retryable=False)


class AIProviderAdapter(ABC):
    """Abstract base class for AI provider adapters.

    All AI provider implementations must inherit from this class and
    implement the abstract methods. Business logic should depend only
    on this interface.
    """

    @abstractmethod
    def generate_text(self, prompt: str, config: dict[str, Any] = None) -> dict:
        """Generate text completion.

        Args:
            prompt: The input prompt.
            config: Optional configuration (model, temperature, etc.).

        Returns:
            dict with keys: content (str), usage (dict), cost (Decimal)
        """

    @abstractmethod
    def generate_structured(
        self, prompt: str, schema: dict = None, config: dict[str, Any] = None
    ) -> dict:
        """Generate structured JSON output.

        Args:
            prompt: The input prompt.
            schema: Optional JSON schema for structured output.
            config: Optional configuration.

        Returns:
            dict with keys: content (dict), usage (dict), cost (Decimal)
        """

    @abstractmethod
    def generate_speech(
        self, text: str, voice_config: dict[str, Any] = None
    ) -> dict:
        """Generate speech audio from text.

        Args:
            text: The text to synthesize.
            voice_config: Optional voice configuration (voice, model, etc.).

        Returns:
            dict with keys: audio (bytes), cost (Decimal)
        """

    @abstractmethod
    def generate_image(
        self, prompt: str, config: dict[str, Any] = None
    ) -> dict:
        """Generate image from prompt.

        Args:
            prompt: The image description.
            config: Optional configuration (size, quality, etc.).

        Returns:
            dict with keys: url (str), cost (Decimal)
        """

    @abstractmethod
    def get_usage_cost(self, usage: dict) -> Decimal:
        """Calculate cost from usage metrics.

        Args:
            usage: Provider-specific usage data.

        Returns:
            Decimal cost in USD.
        """
