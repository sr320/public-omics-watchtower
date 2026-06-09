# Architecture

public-omics-watchtower uses **GitHub as the control plane** and **Mac mini workers** as execution nodes.

## Components

| Component | Technology | Role |
|-----------|------------|------|
| Orchestration | Python 3.11 | Discovery, scoring, worker daemon |
| Workflows | Nextflow | Salmon → DESeq2 → GO enrichment |
| Queue | GitHub Issues | Distributed job queue |
| State | SQLite | Per-node cache and run manifests |
| CI | GitHub Actions | Tests, scheduled discovery, weekly reports |

## Job Flow

```
discover → download → analyze → report
```

Each step is a GitHub Issue with YAML frontmatter. Workers claim issues via labels.

## Multi-Node

- GitHub Issues are authoritative for job state
- SQLite mirrors issue state locally
- Stale claims reclaimed after 24h via housekeeping

See the implementation plan for full diagrams and schema details.
