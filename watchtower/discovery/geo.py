"""GEO discovery via Entrez."""

from __future__ import annotations

from watchtower.config.loader import load_repository_config
from watchtower.discovery.base import DiscoveredRecord, DiscoverySource
from watchtower.discovery.entrez import EntrezClient
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


class GEODiscovery(DiscoverySource):
    source_name = "geo"

    def __init__(self, entrez: EntrezClient | None = None) -> None:
        self.config = load_repository_config("geo")
        self.entrez = entrez or EntrezClient()

    def _build_query(self, organism: str, taxonomy_id: int) -> str:
        template = self.config.get("query_template", "")
        return template.format(organism=organism, taxonomy_id=taxonomy_id).strip()

    def search(self, organism: str, taxonomy_id: int, retmax: int = 100) -> list[DiscoveredRecord]:
        db = self.config.get("database", "gds")
        term = self._build_query(organism, taxonomy_id)
        logger.info("GEO search: %s", term)
        ids = self.entrez.esearch(db, term, retmax=retmax)
        summaries = self.entrez.esummary(db, ids)
        records = []
        for item in summaries:
            accession = item.get("Accession") or item.get("accession") or item.get("uid", "")
            if not accession:
                continue
            n_samples = int(item.get("n_samples", 0) or item.get("samplecount", 0) or 0)
            records.append(
                DiscoveredRecord(
                    source="geo",
                    accession=str(accession),
                    title=item.get("title", ""),
                    organism=item.get("taxon", organism),
                    taxonomy_id=taxonomy_id,
                    summary=item.get("summary", ""),
                    sample_count=n_samples,
                    publication_date=item.get("pdat"),
                    metadata={"entrez_uid": item.get("uid"), "gds_type": item.get("gdsType")},
                )
            )
        return records

    def enrich(self, record: DiscoveredRecord) -> DiscoveredRecord:
        db = self.config.get("database", "gds")
        uid = str(record.metadata.get("entrez_uid", ""))
        if uid:
            summaries = self.entrez.esummary(db, [uid])
            if summaries:
                record.metadata.update(summaries[0])
        return record
