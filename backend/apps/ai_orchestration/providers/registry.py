# -*- coding: utf-8 -*-
"""Provider registry for AI adapter management.

Allows registering and retrieving AI provider adapters by name.
The active provider is determined by the AI_PROVIDER environment variable.
"""
from django.conf import settings

from .base import AIProviderAdapter, AIProviderError
from .openai_provider import OpenAIProviderAdapter


class ProviderRegistry:
    """Registry for AI provider adapters.

    Providers are registered by name and can be retrieved by name.
    The default provider is determined by the AI_PROVIDER setting.
    """

    _providers: dict[str, type[AIProviderAdapter]] = {
        "openai": OpenAIProviderAdapter,
    }

    @classmethod
    def get_provider(cls, name: str = None) -> AIProviderAdapter:
        """Get a provider adapter by name.

        Args:
            name: Provider name. Defaults to AI_PROVIDER setting.

        Returns:
            Instantiated provider adapter.

        Raises:
            AIProviderError: If provider is not found or API key is missing.
        """
        name = name or getattr(settings, "AI_PROVIDER", "openai")

        provider_class = cls._providers.get(name)
        if not provider_class:
            raise AIProviderError(f"Unknown AI provider: {name}")

        # Get API key from settings (environment variable)
        api_key_setting = f"{name.upper()}_API_KEY"
        api_key = getattr(settings, api_key_setting, "")

        if not api_key:
            raise AIProviderError(
                f"API key not configured for provider: {name} "
                f"(set {api_key_setting} environment variable)"
            )

        # Get optional model setting
        model_setting = f"{name.upper()}_MODEL"
        model = getattr(settings, model_setting, None)

        # Get optional timeout setting
        timeout_setting = f"{name.upper()}_TIMEOUT"
        timeout = getattr(settings, timeout_setting, 60.0)

        kwargs = {"api_key": api_key}
        if model:
            kwargs["model"] = model
        if timeout:
            kwargs["timeout"] = timeout

        return provider_class(**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type[AIProviderAdapter]):
        """Register a new provider adapter.

        Args:
            name: Provider name.
            provider_class: Provider adapter class.
        """
        cls._providers[name] = provider_class

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return list of registered provider names."""
        return list(cls._providers.keys())
