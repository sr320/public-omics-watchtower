"""NCBI Entrez E-utilities client."""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from watchtower.discovery.base import RateLimiter
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)

ENTREZ_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESUMMARY_BATCH_SIZE = 200
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_entrez_rate_limiter: RateLimiter | None = None


def get_entrez_rate_limiter(requests_per_sec: float = 3.0) -> RateLimiter:
    """Return a process-wide Entrez rate limiter shared by all clients."""
    global _entrez_rate_limiter
    if _entrez_rate_limiter is None:
        _entrez_rate_limiter = RateLimiter(requests_per_sec)
    return _entrez_rate_limiter


class EntrezClient:
    """Rate-limited Entrez API client."""

    def __init__(
        self,
        email: str = "watchtower@example.com",
        api_key: str | None = None,
        rate_limit_per_sec: float = 3.0,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.email = email
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.rate_limiter = rate_limiter or get_entrez_rate_limiter(rate_limit_per_sec)
        self.session = requests.Session()

    @classmethod
    def from_config(cls) -> EntrezClient:
        """Build a client using watchtower discovery settings."""
        from watchtower.config.loader import load_watchtower_config

        config = load_watchtower_config()
        rate = float(config.get("discovery", {}).get("entrez_rate_limit_per_sec", 3.0))
        return cls(rate_limit_per_sec=rate)

    def _base_params(self) -> dict[str, str]:
        params = {"email": self.email, "tool": "public-omics-watchtower"}
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _get(self, endpoint: str, params: dict[str, Any], max_retries: int = 5) -> str:
        full_params = {**self._base_params(), **params}
        url = f"{ENTREZ_BASE}/{endpoint}"
        delay = 1.0
        response: requests.Response | None = None
        for attempt in range(max_retries):
            self.rate_limiter.wait()
            response = self.session.post(url, data=full_params, timeout=60)
            if response.status_code in RETRYABLE_STATUS_CODES:
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else delay
                logger.warning(
                    "Entrez request failed (%s) on %s, retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    endpoint,
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                delay = min(delay * 2, 60)
                continue
            response.raise_for_status()
            return response.text
        if response is not None:
            response.raise_for_status()
        raise RuntimeError(f"Entrez request to {endpoint} failed without a response")

    def esearch(self, db: str, term: str, retmax: int = 100) -> list[str]:
        text = self._get(
            "esearch.fcgi",
            {"db": db, "term": term, "retmax": retmax, "retmode": "json"},
        )
        import json

        data = json.loads(text)
        return data.get("esearchresult", {}).get("idlist", [])

    def esummary(self, db: str, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        import json

        records: list[dict[str, Any]] = []
        for start in range(0, len(ids), ESUMMARY_BATCH_SIZE):
            batch = ids[start : start + ESUMMARY_BATCH_SIZE]
            text = self._get(
                "esummary.fcgi",
                {"db": db, "id": ",".join(batch), "retmode": "json"},
            )
            data = json.loads(text)
            result = data.get("result", {})
            for uid in result.get("uids", []):
                if uid == "uids":
                    continue
                item = result.get(uid, {})
                if isinstance(item, dict):
                    item["uid"] = uid
                    records.append(item)
        return records

    def elink(self, dbfrom: str, db: str, ids: list[str]) -> list[str]:
        if not ids:
            return []
        import json

        text = self._get(
            "elink.fcgi",
            {
                "dbfrom": dbfrom,
                "db": db,
                "id": ",".join(ids),
                "retmode": "json",
            },
        )
        data = json.loads(text)
        linked: list[str] = []
        for linkset in data.get("linksets", []):
            for linksetdb in linkset.get("linksetdbs", []):
                if linksetdb.get("dbto") == db:
                    linked.extend(str(link_id) for link_id in linksetdb.get("links", []))
        return linked

    def efetch_xml(self, db: str, ids: list[str]) -> ET.Element:
        text = self._get(
            "efetch.fcgi",
            {"db": db, "id": ",".join(ids), "retmode": "xml"},
        )
        return ET.fromstring(text)
