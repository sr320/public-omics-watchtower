"""AI-assisted dataset prioritization (extension point)."""

from __future__ import annotations

from typing import Any

from watchtower.ai.base import AIProvider
from watchtower.config.loader import load_ai_config
from watchtower.discovery.base import DiscoveredRecord


class NullPrioritizer(AIProvider):
    """Default no-op prioritizer for Phase 1."""

    def is_enabled(self) -> bool:
        return False

    def complete(self, prompt: str, system: str | None = None) -> str:
        return ""

    def adjust_score(self, record: DiscoveredRecord, base_score: int) -> tuple[int, str]:
        return base_score, ""


def get_prioritizer() -> AIProvider:
    config = load_ai_config("prioritizer")
    if config.get("enabled") and config.get("provider"):
        raise NotImplementedError("AI prioritizer not implemented in Phase 1")
    return NullPrioritizer()


def maybe_adjust_score(
    record: DiscoveredRecord,
    base_score: int,
    breakdown: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Apply AI score adjustment if provider enabled."""
    prioritizer = get_prioritizer()
    if not prioritizer.is_enabled():
        return base_score, breakdown
    adjusted, note = prioritizer.adjust_score(record, base_score)  # type: ignore[attr-defined]
    breakdown["ai_adjustment"] = note
    return adjusted, breakdown
