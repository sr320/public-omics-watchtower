-- Watchtower SQLite schema v1
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    accession TEXT NOT NULL,
    title TEXT,
    organism TEXT,
    taxonomy_id INTEGER,
    data_type TEXT NOT NULL DEFAULT 'rnaseq',
    relevance_score REAL,
    status TEXT NOT NULL DEFAULT 'discovered',
    metadata_json TEXT,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    github_issue_number TEXT,
    UNIQUE(source, accession)
);

CREATE INDEX IF NOT EXISTS idx_datasets_accession ON datasets(accession);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);
CREATE INDEX IF NOT EXISTS idx_datasets_relevance ON datasets(relevance_score DESC);

CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id),
    run_accession TEXT,
    sample_name TEXT,
    condition TEXT,
    layout TEXT,
    metadata_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_samples_dataset ON samples(dataset_id);

CREATE TABLE IF NOT EXISTS nodes (
    node_id TEXT PRIMARY KEY,
    hostname TEXT,
    capabilities_json TEXT,
    last_heartbeat_at TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    dataset_id TEXT REFERENCES datasets(dataset_id),
    status TEXT NOT NULL DEFAULT 'queued',
    claimed_by_node TEXT REFERENCES nodes(node_id),
    github_issue_number TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    started_at TEXT,
    finished_at TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_type ON jobs(status, job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_claimed ON jobs(claimed_by_node);
CREATE INDEX IF NOT EXISTS idx_jobs_issue ON jobs(github_issue_number);

CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    event_type TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    nextflow_session_id TEXT,
    profile TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    work_dir TEXT,
    params_json TEXT,
    started_at TEXT,
    finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_job ON pipeline_runs(job_id);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id),
    artifact_type TEXT NOT NULL,
    path TEXT NOT NULL,
    checksum TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id, artifact_type);

CREATE TABLE IF NOT EXISTS weekly_reports (
    report_id TEXT PRIMARY KEY,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS report_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL REFERENCES weekly_reports(report_id),
    dataset_id TEXT REFERENCES datasets(dataset_id),
    run_id TEXT REFERENCES pipeline_runs(run_id),
    summary_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_report_items_report ON report_items(report_id);
