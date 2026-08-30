# -*- coding: utf-8 -*-
"""Tests for AI provider adapters (mock-based, no real API calls)."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.ai_orchestration.providers.base import (
    AIProviderAdapter,
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from apps.ai_orchestration.providers.openai_provider import OpenAIProviderAdapter
from apps.ai_orchestration.providers.registry import ProviderRegistry


class TestAIProviderAdapterInterface:
    """Test the abstract adapter interface."""

    def test_cannot_instantiate_abstract(self):
        """AIProviderAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AIProviderAdapter()

    def test_subclass_must_implement_methods(self):
        """Subclass must implement all abstract methods."""

        class IncompleteAdapter(AIProviderAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()


class TestOpenAIProviderAdapter:
    """Test OpenAI adapter with mocked httpx."""

    def test_init_requires_api_key(self):
        """Adapter requires API key."""
        with pytest.raises(AIProviderAuthError):
            OpenAIProviderAdapter(api_key="")

    def test_init_with_valid_key(self):
        """Adapter initializes with valid key."""
        adapter = OpenAIProviderAdapter(api_key="test-key")
        assert adapter.api_key == "test-key"
        assert adapter.model == "gpt-4o"

    def test_init_custom_model(self):
        """Adapter accepts custom model."""
        adapter = OpenAIProviderAdapter(api_key="test-key", model="gpt-4o-mini")
        assert adapter.model == "gpt-4o-mini"

    @patch("apps.ai_orchestration.providers.openai_provider.httpx.Client")
    def test_generate_text_success(self, mock_client_cls):
        """Successful text generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello, world!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        adapter = OpenAIProviderAdapter(api_key="test-key")
        result = adapter.generate_text("Say hello")

        assert result["content"] == "Hello, world!"
        assert "usage" in result
        assert "cost" in result
        assert isinstance(result["cost"], Decimal)

    @patch("apps.ai_orchestration.providers.openai_provider.httpx.Client")
    def test_generate_text_timeout(self, mock_client_cls):
        """Timeout raises AIProviderTimeoutError."""
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        adapter = OpenAIProviderAdapter(api_key="test-key")
        with pytest.raises(AIProviderTimeoutError):
            adapter.generate_text("Say hello")

    @patch("apps.ai_orchestration.providers.openai_provider.httpx.Client")
    def test_generate_text_auth_error(self, mock_client_cls):
        """401 error raises AIProviderAuthError."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        adapter = OpenAIProviderAdapter(api_key="test-key")
        with pytest.raises(AIProviderAuthError):
            adapter.generate_text("Say hello")

    @patch("apps.ai_orchestration.providers.openai_provider.httpx.Client")
    def test_generate_text_rate_limit(self, mock_client_cls):
        """429 error raises AIProviderRateLimitError."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429", request=MagicMock(), response=mock_response
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        adapter = OpenAIProviderAdapter(api_key="test-key")
        with pytest.raises(AIProviderRateLimitError):
            adapter.generate_text("Say hello")

    def test_get_usage_cost(self):
        """Cost calculation from usage metrics."""
        adapter = OpenAIProviderAdapter(api_key="test-key")
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost = adapter.get_usage_cost(usage)
        # gpt-4o: $0.0025/1K input + $0.01/1K output
        expected = Decimal("0.0025") + Decimal("0.005")
        assert cost == expected

    def test_get_usage_cost_empty(self):
        """Empty usage returns zero cost."""
        adapter = OpenAIProviderAdapter(api_key="test-key")
        cost = adapter.get_usage_cost({})
        assert cost == Decimal("0")


class TestProviderRegistry:
    """Test provider registry."""

    def test_get_provider_openai(self):
        """Can get OpenAI provider from registry."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            from django.conf import settings
            settings.OPENAI_API_KEY = "test-key"
            provider = ProviderRegistry.get_provider("openai")
            assert isinstance(provider, OpenAIProviderAdapter)

    def test_get_provider_unknown(self):
        """Unknown provider raises error."""
        with pytest.raises(AIProviderError):
            ProviderRegistry.get_provider("unknown_provider")

    def test_available_providers(self):
        """Can list available providers."""
        providers = ProviderRegistry.available_providers()
        assert "openai" in providers

    def test_register_custom_provider(self):
        """Can register a custom provider."""

        class CustomAdapter(AIProviderAdapter):
            def generate_text(self, prompt, config=None):
                return {"content": "custom", "usage": {}, "cost": Decimal("0")}

            def generate_structured(self, prompt, schema=None, config=None):
                return {"content": {}, "usage": {}, "cost": Decimal("0")}

            def generate_speech(self, text, voice_config=None):
                return {"audio": b"", "cost": Decimal("0")}

            def generate_image(self, prompt, config=None):
                return {"url": "", "cost": Decimal("0")}

            def get_usage_cost(self, usage):
                return Decimal("0")

        ProviderRegistry.register("custom", CustomAdapter)
        assert "custom" in ProviderRegistry.available_providers()
