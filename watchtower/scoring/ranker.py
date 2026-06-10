"""Dataset ranking and queue decisions."""

from __future__ import annotations

import json
from typing import Any

from watchtower.config.loader import load_scoring_config, load_species_config
from watchtower.db.models import Dataset
from watchtower.db.store import Store
from watchtower.discovery.base import DiscoveredRecord
from watchtower.queue.models import QueueJob
from watchtower.scoring.rules import compute_relevance_score
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


class DatasetRanker:
    """Score and rank discovered datasets."""

    def __init__(self, species_id: str) -> None:
        self.species_id = species_id
        self.species_config = load_species_config(species_id)
        self.scoring_config = load_scoring_config()

    def score(self, record: DiscoveredRecord) -> tuple[int, dict[str, Any]]:
        return compute_relevance_score(record, self.species_config, self.scoring_config)

    def should_queue(self, score: int) -> bool:
        threshold = self.scoring_config.get("thresholds", {}).get("auto_queue", 60)
        return score >= threshold

    def should_skip(self, score: int) -> bool:
        threshold = self.scoring_config.get("thresholds", {}).get("skip_below", 20)
        return score < threshold

    def record_to_dataset(self, record: DiscoveredRecord, score: int, breakdown: dict) -> Dataset:
        return Dataset(
            dataset_id=record.dataset_id,
            source=record.source,
            accession=record.accession,
            title=record.title,
            organism=record.organism,
            taxonomy_id=record.taxonomy_id,
            data_type=record.data_type,
            relevance_score=float(score),
            status="scored" if score > 0 else "discovered",
            metadata_json=json.dumps({
                "summary": record.summary,
                "sample_count": record.sample_count,
                "scoring": breakdown,
                "raw_metadata": record.metadata,
            }),
        )

    def create_download_job(self, dataset: Dataset, score: int) -> QueueJob:
        return QueueJob(
            job_id=f"{dataset.accession}:download:rnaseq_v1",
            job_type="download",
            species=self.species_id,
            dataset_id=dataset.dataset_id,
            priority=score,
            payload={
                "source": dataset.source,
                "accession": dataset.accession,
                "pipeline": "rnaseq_salmon_deseq2",
            },
        )

    def process_records(self, records: list[DiscoveredRecord], store: Store) -> list[QueueJob]:
        jobs: list[QueueJob] = []
        for record in records:
            existing = store.get_dataset_by_accession(record.source, record.accession)
            if existing:
                if existing.github_issue_number or existing.status in {
                    "completed",
                    "ready",
                    "failed",
                    "skipped",
                }:
                    logger.debug("Skipping known accession %s", record.accession)
                    continue
                score = int(existing.relevance_score or 0)
                if self.should_queue(score):
                    jobs.append(self.create_download_job(existing, score))
                    logger.info(
                        "Re-queued %s with score %d (missing GitHub issue)",
                        record.accession,
                        score,
                    )
                continue

            score, breakdown = self.score(record)
            dataset = self.record_to_dataset(record, score, breakdown)

            if self.should_skip(score):
                dataset.status = "skipped"
                store.upsert_dataset(dataset)
                continue

            store.upsert_dataset(dataset)

            if self.should_queue(score):
                dataset.status = "queued"
                store.upsert_dataset(dataset)
                jobs.append(self.create_download_job(dataset, score))
                logger.info(
                    "Queued %s with score %d",
                    record.accession,
                    score,
                )

        return jobs
