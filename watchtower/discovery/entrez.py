"""NCBI Entrez E-utilities client."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any
import requests

from watchtower.discovery.base import RateLimiter
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)

ENTREZ_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class EntrezClient:
    """Rate-limited Entrez API client."""

    def __init__(
        self,
        email: str = "watchtower@example.com",
        api_key: str | None = None,
        rate_limit_per_sec: float = 3.0,
    ) -> None:
        self.email = email
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.rate_limiter = RateLimiter(rate_limit_per_sec)
        self.session = requests.Session()

    def _base_params(self) -> dict[str, str]:
        params = {"email": self.email, "tool": "public-omics-watchtower"}
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _get(self, endpoint: str, params: dict[str, Any]) -> str:
        self.rate_limiter.wait()
        full_params = {**self._base_params(), **params}
        url = f"{ENTREZ_BASE}/{endpoint}"
        response = self.session.post(url, data=full_params, timeout=60)
        response.raise_for_status()
        return response.text

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
        text = self._get(
            "esummary.fcgi",
            {"db": db, "id": ",".join(ids), "retmode": "json"},
        )
        import json

        data = json.loads(text)
        result = data.get("result", {})
        records = []
        for uid in result.get("uids", []):
            if uid == "uids":
                continue
            item = result.get(uid, {})
            if isinstance(item, dict):
                item["uid"] = uid
                records.append(item)
        return records

    def efetch_xml(self, db: str, ids: list[str]) -> ET.Element:
        text = self._get(
            "efetch.fcgi",
            {"db": db, "id": ",".join(ids), "retmode": "xml"},
        )
        return ET.fromstring(text)
