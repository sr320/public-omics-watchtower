<table>
  <tr>
    <td width="35%">
      <img src="img/pow.png" width="300" alt="Public Omics Watchtower logo">
    </td>
    <td>
      <h1>Autonomous public omics discovery platform for marine genomics and aquaculture research.</h1>
      <p>
        Continuously monitors NCBI SRA and GEO, prioritizes datasets relevant to marine stress biology, downloads selected studies, and runs reproducible Salmon + DESeq2 workflows on Apple Silicon Mac minis—with GitHub Issues as the distributed work queue.
      </p>
    </td>
  </tr>
</table>

<a href="https://robertslab.github.io/resources/Agentic-Coding-Tools/#five-level-rubric"><img alt="AI Use Level 4: Substantial AI contribution" src="https://img.shields.io/badge/AI%20Use-Level%204%20Substantial%20AI%20Contribution-red"></a>

## Phase 1 Scope

- **Species:** *Crassostrea gigas* (Pacific oyster)
- **Data:** RNA-seq from SRA and GEO
- **Pipeline:** Salmon → DESeq2 → GO enrichment
- **Outputs:** DEG tables, PCA/volcano plots, GO enrichment, Markdown reports, weekly digests

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Validate configuration
watchtower config validate

# Run discovery (local, no GitHub token required for DB-only mode)
watchtower discover --no-create-issue

# Check status
watchtower status

# Run worker (one job)
watchtower worker run --node-id oyster-mini-01 --once
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, security, and component details |
| [deploy/docs/node_setup.md](deploy/docs/node_setup.md) | Mac mini setup (single machine or multi-node) |
| [docs/operations.md](docs/operations.md) | Daily operations and troubleshooting |
| [ROADMAP.md](ROADMAP.md) | Phase 1–3 delivery plan and timeline |
| [REPOSITORY_STRUCTURE.md](REPOSITORY_STRUCTURE.md) | Directory layout and file reference |
| [MILESTONES.md](MILESTONES.md) | Development milestones and success criteria |

## Architecture

- **Control plane:** GitHub (config, code, Issues queue, Actions)
- **Workers:** Mac minis with launchd-managed `watchtower worker` daemons
- **State:** SQLite per node (cache); GitHub Issues authoritative for jobs
- **Pipelines:** Nextflow with `mac_arm64` profile

```
discover → download → analyze → report → weekly digest
```

## Repository Layout

```
config/          YAML configuration (species, repos, scoring, nodes)
watchtower/      Python orchestration package
pipelines/       Nextflow workflows
schemas/         SQLite DDL and JSON Schema
templates/       Jinja2 report templates
deploy/          Mac mini bootstrap and launchd
docs/            Architecture and operations guides
```

## Mac Mini Deployment

See [deploy/docs/node_setup.md](deploy/docs/node_setup.md) for the full guide.

**Single Mac mini (recommended to start):** one worker runs the entire pipeline (discover → download → analyze → report). Create a node config with all four `job_types` (see `config/nodes/_template.yaml`), then:

```bash
./deploy/macos/bootstrap.sh
./deploy/macos/install_worker.sh --node-id oyster-mini-solo
```

**Multi-node — independent fleet:** add more Mac minis in different locations, each with all four `job_types` and its own disk (no shared drive). See [deploy/docs/node_setup.md](deploy/docs/node_setup.md#independent-fleet-full-pipeline-per-machine).

**Multi-node — role-split cluster:** colocated Mac minis only, sharing one `data_root` volume — e.g. `oyster-mini-01` for discovery/download, `oyster-mini-02` for analysis/report.

## CLI Reference

| Command | Description |
|---------|-------------|
| `watchtower config validate` | Validate YAML configuration |
| `watchtower discover` | Search SRA/GEO and score datasets |
| `watchtower status` | Show local database summary |
| `watchtower worker run` | Run worker daemon |
| `watchtower worker housekeeping` | Reclaim stale job claims |
| `watchtower report --weekly` | Generate weekly digest |
| `watchtower retry <job_id>` | Re-queue a failed job |
| `watchtower github store-token` | Save PAT to macOS Keychain |

## Development

```bash
make install
make lint
make test
make validate
```

## Multi-Node Examples

**Independent fleet** (different sites, own disk each):

| Node | Role |
|------|------|
| `oyster-mini-lab-a` | full pipeline |
| `oyster-mini-lab-b` | full pipeline |

**Role-split cluster** (same site, shared volume):

| Node | Role |
|------|------|
| `oyster-mini-01` | discovery + download |
| `oyster-mini-02` | analysis + report |

Configure capabilities in `config/nodes/<node_id>.yaml`.

## License

MIT — University of Washington Marine Genomics Laboratory
