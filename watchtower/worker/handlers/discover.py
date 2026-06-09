"""Discovery job handler."""

from __future__ import annotations

import json

from watchtower.config.loader import load_watchtower_config
from watchtower.db.models import Job, JobEvent
from watchtower.db.store import Store
from watchtower.discovery.geo import GEODiscovery
from watchtower.discovery.sra import SRADiscovery
from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.queue.models import QueueJob
from watchtower.scoring.ranker import DatasetRanker
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


def handle_discover(
    job: QueueJob,
    store: Store,
    queue: GitHubIssuesQueue,
) -> None:
    """Run discovery across enabled repositories and species."""
    wt_config = load_watchtower_config()
    species_list = job.payload.get("species", wt_config.get("enabled_species", []))
    if isinstance(species_list, str):
        species_list = [species_list]

    all_jobs: list[QueueJob] = []
    total_records = 0

    for species_id in species_list:
        ranker = DatasetRanker(species_id)
        from watchtower.config.loader import load_species_config

        sp = load_species_config(species_id)
        organism = sp["scientific_name"]
        taxonomy_id = int(sp["taxonomy_id"])
        retmax = int(wt_config.get("discovery", {}).get("max_results_per_query", 100))

        records = []
        for source_cls in (SRADiscovery, GEODiscovery):
            if not source_cls().config.get("enabled", True):
                continue
            source = source_cls()
            found = source.search(organism, taxonomy_id, retmax=retmax)
            records.extend(found)
            total_records += len(found)

        new_jobs = ranker.process_records(records, store)
        for qjob in new_jobs:
            dataset = store.get_dataset(qjob.dataset_id or "")
            context = f"Auto-queued download for {dataset.accession if dataset else qjob.job_id}"
            issue_num = queue.create_job(qjob, context_md=context)
            if dataset:
                dataset.github_issue_number = str(issue_num)
                dataset.status = "queued"
                store.upsert_dataset(dataset)
            store.upsert_job(
                Job(
                    job_id=qjob.job_id,
                    job_type=qjob.job_type,
                    dataset_id=qjob.dataset_id,
                    status="queued",
                    github_issue_number=str(issue_num),
                    payload_json=json.dumps(qjob.payload),
                )
            )
            all_jobs.append(qjob)

    store.add_job_event(
        JobEvent(
            job_id=job.job_id,
            event_type="discover_complete",
            message=f"Discovered {total_records} records, queued {len(all_jobs)} downloads",
        )
    )
    logger.info(
        "Discovery complete: %d records, %d download jobs",
        total_records,
        len(all_jobs),
    )
