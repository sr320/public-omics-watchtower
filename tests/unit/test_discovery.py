"""Discovery module tests."""

from watchtower.discovery.base import DiscoveredRecord, RateLimiter
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
