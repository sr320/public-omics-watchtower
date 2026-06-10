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

## Deployment

**Single Mac mini:** one launchd-managed worker with a node config listing all job types (`discover`, `download`, `analyze`, `report`) processes the full pipeline. See [deploy/docs/node_setup.md](../deploy/docs/node_setup.md).

**Multi-node:** split `job_types` across machines (e.g. discovery/download on one mini, analysis/report on another). Each node runs its own worker daemon.

In both layouts:

- GitHub Issues are authoritative for job state
- SQLite mirrors issue state locally per node
- Stale claims reclaimed after 24h via housekeeping

See the implementation plan for full diagrams and schema details.
