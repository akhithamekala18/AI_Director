# -*- coding: utf-8 -*-
"""OpenAI provider adapter using httpx (DG-7 resolved).

Implements the AIProviderAdapter interface for OpenAI's API.
Never logs API keys, full prompts, or raw responses.
"""
import logging
from decimal import Decimal
from typing import Any

import httpx

from .base import (
    AIProviderAdapter,
    AIProviderAuthError,
    AIProviderContentError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)

logger = logging.getLogger("apps.ai_orchestration")

# OpenAI pricing per 1K tokens (as of 2026)
_OPENAI_PRICING = {
    "gpt-4o": {"input": Decimal("0.0025"), "output": Decimal("0.01")},
    "gpt-4o-mini": {"input": Decimal("0.00015"), "output": Decimal("0.0006")},
    "tts-1": {"input": Decimal("0.015"), "output": Decimal("0")},
    "tts-1-hd": {"input": Decimal("0.030"), "output": Decimal("0")},
}


class OpenAIProviderAdapter(AIProviderAdapter):
    """OpenAI provider adapter using httpx.

    Uses synchronous httpx client for Celery task compatibility.
    All methods are synchronous to work within Celery's execution model.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", timeout: float = 60.0):
        if not api_key:
            raise AIProviderAuthError("OpenAI API key is required")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = "https://api.openai.com/v1"

    def _get_client(self) -> httpx.Client:
        """Create a new httpx client for each request (thread-safe)."""
        return httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    def _handle_error(self, exc: httpx.HTTPStatusError) -> None:
        """Map HTTP errors to typed provider exceptions."""
        status = exc.response.status_code
        if status == 401:
            raise AIProviderAuthError("OpenAI authentication failed")
        elif status == 429:
            raise AIProviderRateLimitError("OpenAI rate limit exceeded")
        elif status == 400:
            raise AIProviderContentError("OpenAI content policy violation")
        elif status >= 500:
            raise AIProviderError(
                f"OpenAI server error: {status}",
                status_code=status,
                retryable=True,
            )
        raise AIProviderError(
            f"OpenAI API error: {status}", status_code=status
        )

    def generate_text(self, prompt: str, config: dict[str, Any] = None) -> dict:
        """Generate text completion via OpenAI chat completions."""
        config = config or {}
        payload = {
            "model": config.get("model", self.model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.get("temperature", 0.7),
        }
        if "max_tokens" in config:
            payload["max_tokens"] = config["max_tokens"]

        try:
            with self._get_client() as client:
                response = client.post("/chat/completions", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException:
            raise AIProviderTimeoutError("OpenAI request timed out")
        except httpx.HTTPStatusError as exc:
            self._handle_error(exc)

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        cost = self.get_usage_cost(usage)

        return {"content": content, "usage": usage, "cost": cost}

    def generate_structured(
        self, prompt: str, schema: dict = None, config: dict[str, Any] = None
    ) -> dict:
        """Generate structured JSON output via OpenAI."""
        config = config or {}
        payload = {
            "model": config.get("model", self.model),
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": config.get("temperature", 0.3),
        }

        try:
            with self._get_client() as client:
                response = client.post("/chat/completions", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException:
            raise AIProviderTimeoutError("OpenAI request timed out")
        except httpx.HTTPStatusError as exc:
            self._handle_error(exc)

        data = response.json()
        content_str = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        cost = self.get_usage_cost(usage)

        # Parse JSON content
        import json
        try:
            content = json.loads(content_str)
        except json.JSONDecodeError:
            content = {"raw": content_str}

        return {"content": content, "usage": usage, "cost": cost}

    def generate_speech(
        self, text: str, voice_config: dict[str, Any] = None
    ) -> dict:
        """Generate speech audio via OpenAI TTS."""
        voice_config = voice_config or {}
        payload = {
            "model": voice_config.get("model", "tts-1"),
            "input": text,
            "voice": voice_config.get("voice", "alloy"),
        }

        try:
            with self._get_client() as client:
                response = client.post("/audio/speech", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException:
            raise AIProviderTimeoutError("OpenAI TTS request timed out")
        except httpx.HTTPStatusError as exc:
            self._handle_error(exc)

        audio = response.content
        # Estimate cost based on character count
        char_count = len(text)
        cost = Decimal(str(char_count)) * Decimal("0.000015")

        return {"audio": audio, "cost": cost}

    def generate_image(
        self, prompt: str, config: dict[str, Any] = None
    ) -> dict:
        """Generate image via OpenAI DALL-E."""
        config = config or {}
        payload = {
            "model": config.get("model", "dall-e-3"),
            "prompt": prompt,
            "size": config.get("size", "1024x1024"),
            "quality": config.get("quality", "standard"),
        }

        try:
            with self._get_client() as client:
                response = client.post("/images/generations", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException:
            raise AIProviderTimeoutError("OpenAI image request timed out")
        except httpx.HTTPStatusError as exc:
            self._handle_error(exc)

        data = response.json()
        url = data["data"][0]["url"]
        # Estimate cost
        quality = config.get("quality", "standard")
        cost = Decimal("0.04") if quality == "standard" else Decimal("0.08")

        return {"url": url, "cost": cost}

    def get_usage_cost(self, usage: dict) -> Decimal:
        """Calculate cost from OpenAI usage metrics."""
        if not usage:
            return Decimal("0")

        model = self.model
        pricing = _OPENAI_PRICING.get(model, _OPENAI_PRICING["gpt-4o"])

        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        input_cost = Decimal(str(input_tokens)) * pricing["input"] / Decimal("1000")
        output_cost = Decimal(str(output_tokens)) * pricing["output"] / Decimal("1000")

        return input_cost + output_cost
