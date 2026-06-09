"""AI provider base interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract AI provider."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return whether provider is configured and active."""

    @abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> str:
        """Generate text completion."""
