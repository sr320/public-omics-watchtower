"""Worker daemon — poll GitHub Issues and dispatch jobs."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from watchtower.config.loader import load_watchtower_config
from watchtower.db.connection import connect
from watchtower.db.models import Job, JobEvent
from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.queue.models import QueueJob
from watchtower.utils.logging import get_logger, setup_logging
from watchtower.worker.handlers import (
    handle_analyze,
    handle_discover,
    handle_download,
    handle_report,
)
from watchtower.worker.node import NodeManager

logger = get_logger(__name__)


class WorkerDaemon:
    """Long-running worker that claims and processes queue jobs."""

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.wt_config = load_watchtower_config()
        from watchtower.db.store import Store

        self.conn = connect(NodeManager._data_root_for(node_id) / "watchtower.db")
        self.store = Store(self.conn)
        self.node = NodeManager(node_id, self.store)
        self.queue = GitHubIssuesQueue(
            owner=self.wt_config["github"]["owner"],
            repo=self.wt_config["github"]["repo"],
            priority_thresholds=self.wt_config.get("queue", {}).get(
                "priority_thresholds", {}
            ),
        )
        self.poll_interval = int(
            self.wt_config.get("queue", {}).get("poll_interval_sec", 60)
        )
        self.sync_interval = int(
            self.wt_config.get("queue", {}).get("sync_interval_sec", 300)
        )
        self._last_sync = 0.0

    def startup(self) -> None:
        from watchtower.config.validator import validate_watchtower_config

        validate_watchtower_config()
        self.node.register()
        self._sync_queue()
        logger.info("Worker %s started", self.node_id)

    def _sync_queue(self) -> None:
        count = self.queue.sync_jobs_to_store(self.store)
        self._last_sync = time.monotonic()
        logger.debug("Synced %d jobs from GitHub", count)

    def _maybe_sync(self) -> None:
        if time.monotonic() - self._last_sync >= self.sync_interval:
            self._sync_queue()

    def _select_job(self) -> QueueJob | None:
        for job_type in self.node.job_types:
            jobs = self.queue.list_open_jobs(job_type=job_type, status="queued")
            jobs.sort(key=lambda j: j.priority, reverse=True)
            for job in jobs:
                if self.node.preferred_species and job.species not in self.node.preferred_species:
                    continue
                return job
        return None

    def _process_job(self, job: QueueJob) -> None:
        issue_num = job.github_issue_number
        if issue_num is None:
            logger.warning("Job %s has no issue number", job.job_id)
            return

        if not self.queue.claim_job(issue_num, self.node_id, job.job_id):
            logger.debug("Failed to claim issue #%s", issue_num)
            return

        self.store.upsert_job(
            Job(
                job_id=job.job_id,
                job_type=job.job_type,
                dataset_id=job.dataset_id,
                status="running",
                claimed_by_node=self.node_id,
                github_issue_number=str(issue_num),
                payload_json=json.dumps(job.payload),
                started_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.store.add_job_event(
            JobEvent(job_id=job.job_id, event_type="claimed", message=f"node={self.node_id}")
        )

        try:
            result_payload: dict | None = None
            if job.job_type == "discover":
                handle_discover(job, self.store, self.queue)
            elif job.job_type == "download":
                handle_download(job, self.store, self.queue, self.node)
            elif job.job_type == "analyze":
                result_payload = handle_analyze(job, self.store, self.node)
                report_job = QueueJob(
                    job_id=f"{job.payload.get('accession', 'run')}:report:rnaseq_v1",
                    job_type="report",
                    species=job.species,
                    dataset_id=job.dataset_id,
                    priority=job.priority,
                    payload=result_payload or {},
                )
                r_issue = self.queue.create_job(
                    report_job,
                    context_md=f"Report for run {result_payload.get('run_id', '')}",
                )
                self.store.upsert_job(
                    Job(
                        job_id=report_job.job_id,
                        job_type="report",
                        dataset_id=report_job.dataset_id,
                        status="queued",
                        github_issue_number=str(r_issue),
                        payload_json=json.dumps(report_job.payload),
                    )
                )
            elif job.job_type == "report":
                handle_report(job, self.store, self.node)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")

            self.queue.complete_job(issue_num, self.node_id, message=f"Job {job.job_id} done")
            self.store.upsert_job(
                Job(
                    job_id=job.job_id,
                    job_type=job.job_type,
                    dataset_id=job.dataset_id,
                    status="succeeded",
                    claimed_by_node=self.node_id,
                    github_issue_number=str(issue_num),
                    payload_json=json.dumps(job.payload),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s failed", job.job_id)
            self.queue.fail_job(issue_num, self.node_id, str(exc), needs_human=True)
            self.store.upsert_job(
                Job(
                    job_id=job.job_id,
                    job_type=job.job_type,
                    dataset_id=job.dataset_id,
                    status="failed",
                    claimed_by_node=self.node_id,
                    github_issue_number=str(issue_num),
                    error_message=str(exc),
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
            )

    def run_once(self) -> bool:
        """Process at most one job. Returns True if a job was processed."""
        self.node.heartbeat()
        self._maybe_sync()

        if not self.node.has_capacity() or not self.node.has_storage():
            return False

        job = self._select_job()
        if not job:
            return False

        if not self.node.can_handle(job.job_type, job.species):
            return False

        self._process_job(job)
        return True

    def run_loop(self, max_iterations: int | None = None) -> None:
        """Poll until interrupted or max_iterations reached."""
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            processed = self.run_once()
            if not processed:
                time.sleep(self.poll_interval)
            iterations += 1

    def housekeeping(self) -> list[int]:
        """Reclaim stale claims."""
        stale_hours = int(self.wt_config.get("queue", {}).get("stale_claim_hours", 24))
        return self.queue.release_stale_claims(stale_hours=stale_hours)


def run_worker(
    node_id: str,
    once: bool = False,
    max_iterations: int | None = None,
    log_level: str = "INFO",
) -> None:
    setup_logging(log_level)
    daemon = WorkerDaemon(node_id)
    daemon.startup()
    if once:
        daemon.run_once()
    else:
        daemon.run_loop(max_iterations=max_iterations)
