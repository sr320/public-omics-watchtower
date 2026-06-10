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

**Multi-node — independent fleet (recommended for separate locations):** each Mac mini runs the full pipeline on its own disk with a unique `node_id`. Workers share the GitHub Issues queue but do not share storage; download/analyze handoff uses local paths on the machine that staged the data.

**Multi-node — role-split cluster (colocated only):** split `job_types` across machines (e.g. discovery/download on one mini, analysis/report on another) when all nodes mount the same `data_root` volume. Required because analyze jobs reference absolute paths written by the download node.

In all layouts:

- GitHub Issues are authoritative for job state
- SQLite mirrors issue state locally per node (one `watchtower.db` per machine)
- Stale claims reclaimed after 24h via housekeeping

See the implementation plan for full diagrams and schema details.
