"""SQLite CRUD operations."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from watchtower.db.models import (
    Artifact,
    Dataset,
    Job,
    JobEvent,
    Node,
    PipelineRun,
    ReportItem,
    Sample,
    WeeklyReport,
)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class Store:
    """Data access layer for watchtower SQLite database."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # --- datasets ---

    def upsert_dataset(self, dataset: Dataset) -> None:
        self.conn.execute(
            """
            INSERT INTO datasets (
                dataset_id, source, accession, title, organism, taxonomy_id,
                data_type, relevance_score, status, metadata_json,
                discovered_at, github_issue_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')), ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                title=excluded.title,
                organism=excluded.organism,
                relevance_score=excluded.relevance_score,
                status=excluded.status,
                metadata_json=excluded.metadata_json,
                github_issue_number=excluded.github_issue_number
            """,
            (
                dataset.dataset_id,
                dataset.source,
                dataset.accession,
                dataset.title,
                dataset.organism,
                dataset.taxonomy_id,
                dataset.data_type,
                dataset.relevance_score,
                dataset.status,
                dataset.metadata_json,
                dataset.discovered_at,
                dataset.github_issue_number,
            ),
        )
        self.conn.commit()

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        row = self.conn.execute(
            "SELECT * FROM datasets WHERE dataset_id = ?", (dataset_id,)
        ).fetchone()
        if not row:
            return None
        d = _row_to_dict(row)
        return Dataset(**d)

    def get_dataset_by_accession(self, source: str, accession: str) -> Dataset | None:
        row = self.conn.execute(
            "SELECT * FROM datasets WHERE source = ? AND accession = ?",
            (source, accession),
        ).fetchone()
        if not row:
            return None
        return Dataset(**_row_to_dict(row))

    def list_datasets(
        self,
        status: str | None = None,
        min_score: float | None = None,
        limit: int = 100,
    ) -> list[Dataset]:
        query = "SELECT * FROM datasets WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if min_score is not None:
            query += " AND relevance_score >= ?"
            params.append(min_score)
        query += " ORDER BY relevance_score DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [Dataset(**_row_to_dict(r)) for r in rows]

    # --- samples ---

    def upsert_sample(self, sample: Sample) -> None:
        self.conn.execute(
            """
            INSERT INTO samples (
                sample_id, dataset_id, run_accession, sample_name,
                condition, layout, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sample_id) DO UPDATE SET
                condition=excluded.condition,
                metadata_json=excluded.metadata_json
            """,
            (
                sample.sample_id,
                sample.dataset_id,
                sample.run_accession,
                sample.sample_name,
                sample.condition,
                sample.layout,
                sample.metadata_json,
            ),
        )
        self.conn.commit()

    def list_samples(self, dataset_id: str) -> list[Sample]:
        rows = self.conn.execute(
            "SELECT * FROM samples WHERE dataset_id = ?", (dataset_id,)
        ).fetchall()
        return [Sample(**_row_to_dict(r)) for r in rows]

    # --- nodes ---

    def upsert_node(self, node: Node) -> None:
        self.conn.execute(
            """
            INSERT INTO nodes (node_id, hostname, capabilities_json, last_heartbeat_at, status)
            VALUES (?, ?, ?, COALESCE(?, datetime('now')), ?)
            ON CONFLICT(node_id) DO UPDATE SET
                hostname=excluded.hostname,
                capabilities_json=excluded.capabilities_json,
                last_heartbeat_at=excluded.last_heartbeat_at,
                status=excluded.status
            """,
            (
                node.node_id,
                node.hostname,
                node.capabilities_json,
                node.last_heartbeat_at,
                node.status,
            ),
        )
        self.conn.commit()

    def get_node(self, node_id: str) -> Node | None:
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE node_id = ?", (node_id,)
        ).fetchone()
        if not row:
            return None
        return Node(**_row_to_dict(row))

    # --- jobs ---

    def upsert_job(self, job: Job) -> None:
        self.conn.execute(
            """
            INSERT INTO jobs (
                job_id, job_type, dataset_id, status, claimed_by_node,
                github_issue_number, payload_json, created_at,
                started_at, finished_at, error_message
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                COALESCE(?, datetime('now')), ?, ?, ?
            )
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                claimed_by_node=excluded.claimed_by_node,
                github_issue_number=excluded.github_issue_number,
                payload_json=excluded.payload_json,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                error_message=excluded.error_message
            """,
            (
                job.job_id,
                job.job_type,
                job.dataset_id,
                job.status,
                job.claimed_by_node,
                job.github_issue_number,
                job.payload_json,
                job.created_at,
                job.started_at,
                job.finished_at,
                job.error_message,
            ),
        )
        self.conn.commit()

    def get_job(self, job_id: str) -> Job | None:
        row = self.conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if not row:
            return None
        return Job(**_row_to_dict(row))

    def list_jobs(
        self,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[Job]:
        query = "SELECT * FROM jobs WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if job_type:
            query += " AND job_type = ?"
            params.append(job_type)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        return [Job(**_row_to_dict(r)) for r in rows]

    def count_running_jobs(self, node_id: str) -> int:
        row = self.conn.execute(
            """
            SELECT COUNT(*) FROM jobs
            WHERE claimed_by_node = ? AND status IN ('claimed', 'running')
            """,
            (node_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    def add_job_event(self, event: JobEvent) -> None:
        self.conn.execute(
            """
            INSERT INTO job_events (job_id, event_type, message)
            VALUES (?, ?, ?)
            """,
            (event.job_id, event.event_type, event.message),
        )
        self.conn.commit()

    def list_job_events(self, job_id: str) -> list[JobEvent]:
        rows = self.conn.execute(
            "SELECT * FROM job_events WHERE job_id = ? ORDER BY created_at",
            (job_id,),
        ).fetchall()
        return [JobEvent(**_row_to_dict(r)) for r in rows]

    # --- pipeline runs ---

    def upsert_pipeline_run(self, run: PipelineRun) -> None:
        self.conn.execute(
            """
            INSERT INTO pipeline_runs (
                run_id, job_id, nextflow_session_id, profile, status,
                work_dir, params_json, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                nextflow_session_id=excluded.nextflow_session_id,
                finished_at=excluded.finished_at
            """,
            (
                run.run_id,
                run.job_id,
                run.nextflow_session_id,
                run.profile,
                run.status,
                run.work_dir,
                run.params_json,
                run.started_at,
                run.finished_at,
            ),
        )
        self.conn.commit()

    def get_pipeline_run(self, run_id: str) -> PipelineRun | None:
        row = self.conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        return PipelineRun(**_row_to_dict(row))

    def list_pipeline_runs(self, job_id: str) -> list[PipelineRun]:
        rows = self.conn.execute(
            "SELECT * FROM pipeline_runs WHERE job_id = ?", (job_id,)
        ).fetchall()
        return [PipelineRun(**_row_to_dict(r)) for r in rows]

    # --- artifacts ---

    def add_artifact(self, artifact: Artifact) -> None:
        self.conn.execute(
            """
            INSERT INTO artifacts (artifact_id, run_id, artifact_type, path, checksum)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET path=excluded.path
            """,
            (
                artifact.artifact_id,
                artifact.run_id,
                artifact.artifact_type,
                artifact.path,
                artifact.checksum,
            ),
        )
        self.conn.commit()

    def list_artifacts(self, run_id: str) -> list[Artifact]:
        rows = self.conn.execute(
            "SELECT * FROM artifacts WHERE run_id = ?", (run_id,)
        ).fetchall()
        return [Artifact(**_row_to_dict(r)) for r in rows]

    # --- weekly reports ---

    def upsert_weekly_report(self, report: WeeklyReport) -> None:
        self.conn.execute(
            """
            INSERT INTO weekly_reports (report_id, week_start, week_end, path, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(report_id) DO UPDATE SET
                path=excluded.path,
                status=excluded.status
            """,
            (report.report_id, report.week_start, report.week_end, report.path, report.status),
        )
        self.conn.commit()

    def add_report_item(self, item: ReportItem) -> None:
        self.conn.execute(
            """
            INSERT INTO report_items (report_id, dataset_id, run_id, summary_json)
            VALUES (?, ?, ?, ?)
            """,
            (item.report_id, item.dataset_id, item.run_id, item.summary_json),
        )
        self.conn.commit()

    def list_completed_reports_since(self, since: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT d.*, j.job_id, pr.run_id
            FROM datasets d
            JOIN jobs j ON j.dataset_id = d.dataset_id
            JOIN pipeline_runs pr ON pr.job_id = j.job_id
            WHERE d.status = 'completed' AND j.finished_at >= ?
            ORDER BY d.relevance_score DESC
            """,
            (since,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def dataset_to_metadata(self, dataset: Dataset) -> dict[str, Any]:
        if dataset.metadata_json:
            return json.loads(dataset.metadata_json)
        return {}
