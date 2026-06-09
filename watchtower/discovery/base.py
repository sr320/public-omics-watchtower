"""Base discovery interfaces."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveredRecord:
    source: str
    accession: str
    title: str
    organism: str
    taxonomy_id: int
    data_type: str = "rnaseq"
    summary: str = ""
    sample_count: int = 0
    publication_date: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"{self.source}:{self.accession}"


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, requests_per_sec: float = 3.0) -> None:
        self.min_interval = 1.0 / requests_per_sec
        self._last_request = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()


class DiscoverySource(ABC):
    """Abstract public repository discovery source."""

    source_name: str

    @abstractmethod
    def search(self, organism: str, taxonomy_id: int, retmax: int = 100) -> list[DiscoveredRecord]:
        """Search repository for matching records."""

    @abstractmethod
    def enrich(self, record: DiscoveredRecord) -> DiscoveredRecord:
        """Fetch additional metadata for a record."""
