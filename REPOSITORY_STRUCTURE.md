# Repository Structure

This document describes the layout of **public-omics-watchtower** and the purpose of each major directory and file.

---

## Top-Level Layout

```
public-omics-watchtower/
├── ARCHITECTURE.md          # System design (this repo)
├── ROADMAP.md               # Phase 1–3 delivery plan
├── REPOSITORY_STRUCTURE.md  # This file
├── MILESTONES.md            # Development milestones
├── README.md                # Quick start and CLI reference
├── LICENSE
├── Makefile                 # install, lint, test, validate
├── pyproject.toml           # Python package definition
├── environment.yml          # Conda environment (Apple Silicon)
│
├── config/                  # YAML configuration (no secrets)
├── schemas/                 # SQLite DDL and JSON Schema
├── watchtower/              # Python orchestration package
├── pipelines/               # Nextflow workflows
├── references/              # Per-species reference manifests
├── templates/               # Jinja2 report templates
├── deploy/                  # Mac mini deployment scripts
├── scripts/                 # Utility scripts (label setup, etc.)
├── tests/                   # Unit and integration tests
├── docs/                    # Supplementary documentation
└── .github/                 # Actions, issue templates, labels
```

---

## Configuration (`config/`)

All runtime behavior is driven by layered YAML. No secrets are stored here.

```
config/
├── watchtower.yaml                 # Global: GitHub repo, thresholds, logging, enabled species
├── species/
│   └── crassostrea_gigas.yaml      # Taxonomy, synonyms, stress keywords, reference path
├── repositories/
│   ├── sra.yaml                    # SRA Entrez query template and field mapping
│   └── geo.yaml                    # GEO Entrez query template and field mapping
├── scoring/
│   └── relevance.yaml              # Weighted scoring rules and queue thresholds
├── pipelines/
│   └── rnaseq_salmon_deseq2.yaml   # Nextflow paths, Salmon/DESeq2 params, contrasts
├── nodes/
│   ├── _template.yaml              # Node config template (full pipeline per node)
│   ├── oyster-mini-01.yaml         # Role-split example: discover + download (shared storage)
│   └── oyster-mini-02.yaml         # Role-split example: analyze + report (shared storage)
└── ai/
    ├── prioritizer.yaml            # AI prioritization provider (stub in Phase 1)
    └── reporter.yaml               # AI report interpretation provider (stub)
```

**Validate:** `watchtower config validate`

---

## Schemas (`schemas/`)

```
schemas/
├── issue_body.schema.json          # JSON Schema for GitHub Issue YAML frontmatter
└── sqlite/
    └── 001_initial.sql             # SQLite schema v1 (datasets, jobs, runs, artifacts, ...)
```

The migration runner in `watchtower/db/migrations.py` applies `*.sql` files in version order on first connect.

---

## Python Package (`watchtower/`)

```
watchtower/
├── __init__.py                     # Package version
├── cli.py                          # `watchtower` CLI entrypoint
├── housekeeping.py                 # Stale claim recovery across fleet
│
├── config/
│   ├── loader.py                   # YAML loading and composition
│   └── validator.py                # Config and issue body validation
│
├── db/
│   ├── models.py                   # Dataclasses and status enums
│   ├── connection.py               # SQLite connect + migrate
│   ├── migrations.py               # Schema migration runner
│   └── store.py                    # CRUD access layer
│
├── discovery/
│   ├── base.py                     # DiscoveredRecord, RateLimiter, DiscoverySource ABC
│   ├── entrez.py                   # NCBI Entrez E-utilities client
│   ├── sra.py                      # SRA discovery
│   └── geo.py                      # GEO discovery
│
├── scoring/
│   ├── rules.py                    # Taxonomy, keyword, sample-count scoring
│   └── ranker.py                   # DatasetRanker: score, queue, create download jobs
│
├── queue/
│   ├── models.py                   # QueueJob, label helpers
│   └── github_issues.py            # GitHub Issues queue client (claim, complete, sync)
│
├── worker/
│   ├── daemon.py                   # WorkerDaemon poll loop
│   ├── node.py                     # NodeManager: heartbeat, capacity, routing
│   └── handlers/
│       ├── discover.py             # Discovery job handler
│       ├── download.py             # SRA/GEO download handler
│       ├── analyze.py              # Nextflow pipeline handler
│       └── report.py               # Report sync handler
│
├── download/
│   ├── staging.py                  # Directory layout, sample sheet writer
│   ├── sra.py                      # prefetch / fasterq-dump wrappers
│   └── geo_download.py             # GEO → linked SRA download
│
├── reporting/
│   ├── weekly.py                   # Weekly digest generator
│   ├── sync_reports.py             # Push artifacts to reports branch
│   └── plots.py                    # Plot artifact discovery helpers
│
├── ai/
│   ├── base.py                     # AIProvider ABC
│   ├── prioritizer.py              # NullPrioritizer (Phase 1 stub)
│   └── interpreter.py              # NullInterpreter (Phase 1 stub)
│
└── utils/
    ├── logging.py                  # Logging setup
    └── paths.py                    # Repo root discovery, safe path helpers
```

**Entry point:** `watchtower` command (defined in `pyproject.toml`)

---

## Pipelines (`pipelines/`)

```
pipelines/
└── rnaseq/
    ├── main.nf                     # Nextflow DSL2 workflow entry
    ├── nextflow.config             # Params, profiles, manifest
    ├── conf/
    │   ├── base.config             # Shared process defaults
    │   └── mac_arm64.config        # Apple Silicon local executor tuning
    ├── modules/
    │   ├── qc.nf                   # FastQC
    │   ├── salmon.nf               # Salmon quantification
    │   ├── deseq2.nf               # DESeq2 analysis
    │   ├── enrichment.nf           # GO enrichment
    │   └── reporting.nf            # Markdown report render
    └── bin/
        ├── deseq2_analysis.R       # DESeq2, PCA, volcano R script
        ├── go_enrichment.R         # GO enrichment R script
        └── render_report.py        # Study report Markdown generator
```

**Run profile:** `-profile mac_arm64`

**Standard outputs:** `{run_dir}/results/{quant,deg,plots,enrichment,qc,report}/`

---

## References (`references/`)

Per-species reference data manifests. Index files are built locally, not committed.

```
references/
└── crassostrea_gigas/
    ├── manifest.yaml               # Genome accession, Salmon index path, GO annotation status
    └── README.md                   # Salmon index build instructions
```

Phase 2 will add `references/{ostrea_lurida,mytilus,...}/`.

---

## Templates (`templates/`)

```
templates/
└── reports/
    ├── study_report.md.j2          # Per-study report template
    └── weekly_digest.md.j2         # Weekly lab digest template
```

Rendered by `watchtower.reporting.weekly` and `pipelines/rnaseq/bin/render_report.py`.

---

## Deployment (`deploy/`)

```
deploy/
├── macos/
│   ├── bootstrap.sh                # Homebrew, mamba, Nextflow, conda env install
│   ├── install_worker.sh           # Install launchd worker plist
│   └── launchd/
│       └── com.uw.watchtower.worker.plist
└── docs/
    └── node_setup.md               # Mac mini one-time setup guide
```

---

## Scripts (`scripts/`)

```
scripts/
└── setup_labels.sh                 # Create standard GitHub labels via `gh`
```

---

## Tests (`tests/`)

```
tests/
├── fixtures/
│   ├── mock_issue_body.yaml        # Valid issue frontmatter for queue tests
│   └── geo_soft_samples.txt        # Sample GEO SOFT excerpt
├── unit/
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_discovery.py
│   ├── test_queue.py
│   ├── test_scoring.py
│   ├── test_staging.py
│   ├── test_weekly.py
│   └── test_worker_node.py
└── integration/
    └── test_github_queue_mock.py   # GitHub queue claim protocol (mocked API)
```

**Run:** `make test` or `pytest tests/`

---

## Documentation (`docs/`)

Supplementary guides. Top-level `ARCHITECTURE.md`, `ROADMAP.md`, etc. are the canonical design documents.

```
docs/
├── architecture.md                 # Brief architecture summary (links to ARCHITECTURE.md)
├── operations.md                 # Day-to-day operator commands
├── configuration.md                # Config layer reference
├── phase2_species.md               # Phase 2 species expansion notes
└── phase3_meta_analysis.md         # Phase 3 meta-analysis notes
```

---

## GitHub (`.github/`)

```
.github/
├── workflows/
│   ├── ci.yml                      # Ruff, pytest, config validate, Nextflow dry-run
│   ├── discovery_schedule.yml      # Daily cron: create discovery issues
│   └── weekly_report.yml           # Weekly cron: digest + housekeeping
├── ISSUE_TEMPLATE/
│   ├── discovery_job.yml
│   ├── download_job.yml
│   ├── analysis_job.yml
│   └── report_job.yml
└── labels.yml                      # Standard label definitions (reference)
```

---

## Data Directories (Not in Git)

These paths are created at runtime on worker nodes and are listed in `.gitignore`:

```
{data_root}/                        # Default: /Volumes/omics/watchtower
├── watchtower.db
├── raw/{sra,geo}/{accession}/
├── runs/{run_id}/
├── reports/{studies,weekly}/
├── logs/worker.log
└── backups/
```

---

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `config/watchtower.yaml` | Start here for global settings |
| `config/species/crassostrea_gigas.yaml` | Phase 1 species profile |
| `config/nodes/oyster-mini-01.yaml` | Role-split node example (requires shared `data_root`) |
| `config/nodes/_template.yaml` | Full-pipeline node template for single or independent-fleet deploys |
| `schemas/issue_body.schema.json` | Job issue validation schema |
| `schemas/sqlite/001_initial.sql` | Database schema |
| `watchtower/cli.py` | All operator commands |
| `watchtower/worker/daemon.py` | Worker poll loop |
| `watchtower/queue/github_issues.py` | Queue claim protocol |
| `pipelines/rnaseq/main.nf` | Bioinformatics workflow |
| `references/crassostrea_gigas/manifest.yaml` | Reference genome and index paths |

---

## Adding New Components

| To add… | Create… |
|---------|---------|
| New species | `config/species/{id}.yaml`, `references/{id}/manifest.yaml`, GitHub label `species:{id}` |
| New repository | `config/repositories/{source}.yaml`, `watchtower/discovery/{source}.py` |
| New pipeline | `config/pipelines/{id}.yaml`, `pipelines/{name}/`, handler in `watchtower/worker/handlers/` |
| New worker node | Copy `config/nodes/_template.yaml` → `config/nodes/{node_id}.yaml`, run `install_worker.sh` |
| New job type | Update `schemas/issue_body.schema.json`, add handler, add `job:{type}` label |

See [ARCHITECTURE.md](ARCHITECTURE.md) for design rationale and [ROADMAP.md](ROADMAP.md) for planned extensions.
