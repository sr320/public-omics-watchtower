"""Data models for SQLite entities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Dataset:
    dataset_id: str
    source: str
    accession: str
    title: str | None = None
    organism: str | None = None
    taxonomy_id: int | None = None
    data_type: str = "rnaseq"
    relevance_score: float | None = None
    status: str = "discovered"
    metadata_json: str | None = None
    discovered_at: str | None = None
    github_issue_number: str | None = None


@dataclass
class Sample:
    sample_id: str
    dataset_id: str
    run_accession: str | None = None
    sample_name: str | None = None
    condition: str | None = None
    layout: str | None = None
    metadata_json: str | None = None


@dataclass
class Node:
    node_id: str
    hostname: str | None = None
    capabilities_json: str | None = None
    last_heartbeat_at: str | None = None
    status: str = "active"


@dataclass
class Job:
    job_id: str
    job_type: str
    dataset_id: str | None = None
    status: str = "queued"
    claimed_by_node: str | None = None
    github_issue_number: str | None = None
    payload_json: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None


@dataclass
class JobEvent:
    job_id: str
    event_type: str
    message: str | None = None
    id: int | None = None
    created_at: str | None = None


@dataclass
class PipelineRun:
    run_id: str
    job_id: str
    nextflow_session_id: str | None = None
    profile: str | None = None
    status: str = "pending"
    work_dir: str | None = None
    params_json: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


@dataclass
class Artifact:
    artifact_id: str
    run_id: str
    artifact_type: str
    path: str
    checksum: str | None = None
    created_at: str | None = None


@dataclass
class WeeklyReport:
    report_id: str
    week_start: str
    week_end: str
    path: str | None = None
    status: str = "pending"
    created_at: str | None = None


@dataclass
class ReportItem:
    report_id: str
    dataset_id: str | None = None
    run_id: str | None = None
    summary_json: str | None = None
    id: int | None = None


DATASET_STATUSES = frozenset({
    "discovered", "scored", "queued", "downloading", "ready",
    "analyzing", "completed", "failed", "skipped",
})

JOB_STATUSES = frozenset({
    "queued", "claimed", "running", "succeeded", "failed", "cancelled",
})

PIPELINE_STATUSES = frozenset({"pending", "running", "succeeded", "failed"})

JOB_TYPES = frozenset({"discover", "download", "analyze", "report"})
