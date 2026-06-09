"""Download job handler."""

from __future__ import annotations

import json

from watchtower.db.models import Job, JobEvent
from watchtower.db.store import Store
from watchtower.download.geo_download import download_geo_dataset
from watchtower.download.sra import download_sra_accession
from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.queue.models import QueueJob
from watchtower.utils.logging import get_logger
from watchtower.worker.node import NodeManager

logger = get_logger(__name__)


def handle_download(
    job: QueueJob,
    store: Store,
    queue: GitHubIssuesQueue,
    node: NodeManager,
) -> QueueJob | None:
    """Download dataset and enqueue analysis job."""
    source = job.payload.get("source", "sra")
    accession = job.payload.get("accession", "")
    data_root = node.data_root

    dataset = store.get_dataset(job.dataset_id or f"{source}:{accession}")
    if dataset:
        dataset.status = "downloading"
        store.upsert_dataset(dataset)

    if source == "geo":
        metadata = ""
        if dataset and dataset.metadata_json:
            metadata = json.loads(dataset.metadata_json).get("summary", "")
        sheet_path, samples = download_geo_dataset(
            data_root, accession, metadata_text=metadata
        )
    else:
        sheet_path, samples = download_sra_accession(data_root, accession)

    if dataset:
        dataset.status = "ready"
        store.upsert_dataset(dataset)

    analyze_job = QueueJob(
        job_id=f"{accession}:analyze:rnaseq_v1",
        job_type="analyze",
        species=job.species,
        dataset_id=job.dataset_id,
        priority=job.priority,
        payload={
            "source": source,
            "accession": accession,
            "samplesheet": str(sheet_path),
            "sample_count": len(samples),
            "pipeline": job.payload.get("pipeline", "rnaseq_salmon_deseq2"),
        },
    )

    context = f"Analysis for {accession} ({len(samples)} samples)"
    issue_num = queue.create_job(analyze_job, context_md=context)
    store.upsert_job(
        Job(
            job_id=analyze_job.job_id,
            job_type="analyze",
            dataset_id=analyze_job.dataset_id,
            status="queued",
            github_issue_number=str(issue_num),
            payload_json=json.dumps(analyze_job.payload),
        )
    )
    store.add_job_event(
        JobEvent(
            job_id=job.job_id,
            event_type="download_complete",
            message=f"Staged {len(samples)} samples at {sheet_path}",
        )
    )
    logger.info("Download complete for %s", accession)
    return analyze_job
