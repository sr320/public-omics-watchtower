"""SRA discovery via Entrez."""

from __future__ import annotations

from watchtower.config.loader import load_repository_config
from watchtower.discovery.base import DiscoveredRecord, DiscoverySource
from watchtower.discovery.entrez import EntrezClient
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


class SRADiscovery(DiscoverySource):
    source_name = "sra"

    def __init__(self, entrez: EntrezClient | None = None) -> None:
        self.config = load_repository_config("sra")
        self.entrez = entrez or EntrezClient()

    def _build_query(self, organism: str, taxonomy_id: int) -> str:
        template = self.config.get("query_template", "")
        return template.format(organism=organism, taxonomy_id=taxonomy_id).strip()

    def search(self, organism: str, taxonomy_id: int, retmax: int = 100) -> list[DiscoveredRecord]:
        db = self.config.get("database", "sra")
        term = self._build_query(organism, taxonomy_id)
        logger.info("SRA search: %s", term)
        ids = self.entrez.esearch(db, term, retmax=retmax)
        summaries = self.entrez.esummary(db, ids)
        records = []
        for item in summaries:
            accession = item.get("acc") or item.get("runaccession") or item.get("uid", "")
            if not accession:
                continue
            records.append(
                DiscoveredRecord(
                    source="sra",
                    accession=str(accession),
                    title=item.get("title", ""),
                    organism=item.get("organism", organism),
                    taxonomy_id=taxonomy_id,
                    summary=item.get("summary", ""),
                    sample_count=int(item.get("total_spots", 0) or 0),
                    metadata={"entrez_uid": item.get("uid"), "platform": item.get("platform")},
                )
            )
        return records

    def enrich(self, record: DiscoveredRecord) -> DiscoveredRecord:
        db = self.config.get("database", "sra")
        summaries = self.entrez.esummary(db, [record.metadata.get("entrez_uid", record.accession)])
        if summaries:
            item = summaries[0]
            record.summary = item.get("summary", record.summary)
            record.metadata.update(item)
        return record
