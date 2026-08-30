# -*- coding: utf-8 -*-
"""Provider-agnostic scene media abstraction (Phase 2F, Task 25 / §24.3, §41.2).

Business logic depends on this abstraction, never on provider-specific HTTP
implementations — mirroring the frozen Phase 2A ``AIProviderAdapter`` pattern
(§41.2 "provider-agnostic model adapter so model selection does not change
workflow"). Scene media has its own per-media-type contract because a single
scene yields up to four asset kinds: visual, voice, music, subtitle.

Each method receives a per-scene media payload (built by the deterministic
engine) and returns a dict describing the generated asset and lightweight
provider metadata. No provider credentials are ever stored or returned; they
must come from settings/environment and remain under provider ownership.
"""
from abc import ABC, abstractmethod


class SceneMediaProviderError(Exception):
    """Base error for scene media generation failures.

    ``retryable`` informs the AsyncJob retry substrate (frozen Phase 2A) about
    whether re-running the job is likely to succeed.
    """

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class SceneMediaProvider(ABC):
    """Abstract base class for scene media providers.

    Implementations must be deterministic under test; a provider may produce
    real assets (stored on an external service) or mock references.
    """

    @abstractmethod
    def generate_visual(self, payload: dict) -> dict:
        """Generate the scene's visual asset.

        Returns a dict with ``asset_ref`` (str) and ``provider_metadata`` (dict).
        """

    @abstractmethod
    def generate_voice(self, payload: dict) -> dict:
        """Generate the scene's voice-over from narration.

        Returns a dict with ``asset_ref``, ``voice`` (dict) and
        ``provider_metadata`` (dict).
        """

    @abstractmethod
    def generate_music(self, payload: dict) -> dict:
        """Generate/select the scene's background music.

        Returns a dict with ``asset_ref``, ``music`` (dict) and
        ``provider_metadata`` (dict).
        """

    @abstractmethod
    def generate_subtitle(self, payload: dict) -> dict:
        """Produce the scene's subtitles/captions from narration.

        Returns a dict with ``asset_ref``, ``caption`` (dict) and
        ``provider_metadata`` (dict).
        """
