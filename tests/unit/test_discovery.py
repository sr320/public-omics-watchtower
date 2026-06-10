"""Discovery module tests."""

from unittest.mock import MagicMock

import pytest
import requests

from watchtower.discovery.base import DiscoveredRecord, RateLimiter
from watchtower.discovery.entrez import EntrezClient
from watchtower.discovery.geo import GEODiscovery
from watchtower.discovery.sra import SRADiscovery


class MockEntrez:
    def esearch(self, db: str, term: str, retmax: int = 100) -> list[str]:
        return ["12345"]

    def esummary(self, db: str, ids: list[str]) -> list[dict]:
        if db == "sra":
            return [{
                "uid": "12345",
                "acc": "SRR12345",
                "title": "Crassostrea gigas heat stress RNA-seq",
                "organism": "Crassostrea gigas",
                "summary": "Hypoxia treatment",
                "total_spots": 100,
            }]
        return [{
            "uid": "67890",
            "Accession": "GSE12345",
            "title": "Oyster transcriptome stress",
            "taxon": "Crassostrea gigas",
            "summary": "Salinity stress",
            "n_samples": 6,
            "pdat": "2024",
        }]


def test_sra_discovery_search() -> None:
    source = SRADiscovery(entrez=MockEntrez())  # type: ignore[arg-type]
    records = source.search("Crassostrea gigas", 29159)
    assert len(records) == 1
    assert records[0].accession == "SRR12345"
    assert records[0].dataset_id == "sra:SRR12345"


def test_geo_discovery_search() -> None:
    source = GEODiscovery(entrez=MockEntrez())  # type: ignore[arg-type]
    records = source.search("Crassostrea gigas", 29159)
    assert len(records) == 1
    assert records[0].accession == "GSE12345"


def test_rate_limiter() -> None:
    limiter = RateLimiter(requests_per_sec=100)
    limiter.wait()
    limiter.wait()


def test_discovered_record_id() -> None:
    r = DiscoveredRecord(
        source="geo", accession="GSE1", title="t", organism="o", taxonomy_id=1
    )
    assert r.dataset_id == "geo:GSE1"


def test_entrez_retries_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    import watchtower.discovery.entrez as entrez_mod

    monkeypatch.setattr(entrez_mod, "_entrez_rate_limiter", None)
    client = EntrezClient(rate_limit_per_sec=1000)
    ok = requests.Response()
    ok.status_code = 200
    ok._content = b'{"esearchresult": {"idlist": []}}'

    rate_limited = requests.Response()
    rate_limited.status_code = 429
    rate_limited.headers = {"Retry-After": "0"}
    rate_limited.reason = "Too Many Requests"

    mock_post = MagicMock(side_effect=[rate_limited, ok])
    client.session.post = mock_post
    monkeypatch.setattr("watchtower.discovery.entrez.time.sleep", lambda _: None)

    result = client.esearch("gds", "test")
    assert result == []
    assert mock_post.call_count == 2


def test_entrez_retries_on_502(monkeypatch: pytest.MonkeyPatch) -> None:
    import watchtower.discovery.entrez as entrez_mod

    monkeypatch.setattr(entrez_mod, "_entrez_rate_limiter", None)
    client = EntrezClient(rate_limit_per_sec=1000)
    ok = requests.Response()
    ok.status_code = 200
    ok._content = b'{"esearchresult": {"idlist": []}}'

    bad_gateway = requests.Response()
    bad_gateway.status_code = 502
    bad_gateway.headers = {}
    bad_gateway.reason = "Bad Gateway"

    mock_post = MagicMock(side_effect=[bad_gateway, ok])
    client.session.post = mock_post
    monkeypatch.setattr("watchtower.discovery.entrez.time.sleep", lambda _: None)

    result = client.esearch("gds", "test")
    assert result == []
    assert mock_post.call_count == 2


def test_entrez_clients_share_rate_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    import watchtower.discovery.entrez as entrez_mod

    monkeypatch.setattr(entrez_mod, "_entrez_rate_limiter", None)
    first = EntrezClient(rate_limit_per_sec=3.0)
    second = EntrezClient(rate_limit_per_sec=3.0)
    assert first.rate_limiter is second.rate_limiter
