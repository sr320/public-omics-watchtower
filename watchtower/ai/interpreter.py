"""AI biological interpretation (extension point)."""

from __future__ import annotations

from typing import Any

from watchtower.ai.base import AIProvider
from watchtower.config.loader import load_ai_config


class NullInterpreter(AIProvider):
    """Default no-op interpreter for Phase 1."""

    def is_enabled(self) -> bool:
        return False

    def complete(self, prompt: str, system: str | None = None) -> str:
        return ""

    def summarize_deg_results(self, context: dict[str, Any]) -> str:
        return ""

    def suggest_biomarkers(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        return []


def get_interpreter() -> NullInterpreter:
    config = load_ai_config("reporter")
    if config.get("enabled") and config.get("provider"):
        raise NotImplementedError("AI interpreter not implemented in Phase 1")
    return NullInterpreter()
