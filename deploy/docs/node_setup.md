# Mac Mini Node Setup

You can run public-omics-watchtower on **one Mac mini** (full pipeline) or scale across **multiple Mac minis**. Start with a single node unless you need more throughput.

There are three deployment patterns:

| Pattern | When to use | Storage |
|---------|-------------|---------|
| **Single node** | Getting started; one machine | Local SSD or external volume |
| **Independent fleet** | Multiple Mac minis in different locations | Each machine has its own disk — **no shared drive** |
| **Role-split cluster** | Two+ Mac minis at the same site with a shared volume | Same `data_root` mount on every machine |

Use **independent fleet** when nodes are in different buildings or cities. Use **role-split** only when all Mac minis can read the same files at the same path (e.g. one Thunderbolt enclosure or NAS mounted at `/Volumes/omics/watchtower` on each machine).

## Prerequisites

- Apple Silicon Mac mini (macOS 13+)
- External data volume mounted at `/Volumes/omics/watchtower` (recommended; RNA-seq data fills internal storage quickly)
- GitHub fine-grained PAT with Issues and Contents access
- NCBI API key (optional, improves Entrez rate limits)

## One-Time Setup

```bash
# Clone repository
sudo mkdir -p /opt/watchtower
sudo chown "$USER" /opt/watchtower
git clone https://github.com/sr320/public-omics-watchtower.git /opt/watchtower/app
cd /opt/watchtower/app

# Bootstrap tools and conda environment
chmod +x deploy/macos/*.sh
./deploy/macos/bootstrap.sh

# Store GitHub token in Keychain (Issues + Contents scope on this repo)
watchtower github store-token
watchtower github get-token   # should report "Token found"

# Build Salmon index (see references/crassostrea_gigas/README.md)
```

## Single Mac Mini (full pipeline)

One worker on one machine can handle every job type: discover → download → analyze → report.

### 1. Create a node config

Copy the template and set a unique `node_id` and your Mac's hostname:

```bash
cp config/nodes/_template.yaml config/nodes/oyster-mini-solo.yaml
```

Edit `config/nodes/oyster-mini-solo.yaml`:

```yaml
node_id: oyster-mini-solo
hostname: my-mac-mini.local   # scutil --get LocalHostName
data_root: /Volumes/omics/watchtower
capabilities:
  job_types:
    - discover
    - download
    - analyze
    - report
  max_concurrent_jobs: 1      # start with 1; raise after smoke test if disk/CPU allow
  storage_gb_free_min: 200
  preferred_species:
    - crassostrea_gigas
profiles:
  - mac_arm64
```

All four `job_types` must be present on a single node, or jobs for missing types will sit unclaimed in the GitHub queue.

Ensure the `species:crassostrea_gigas` label exists in the repository (GitHub → Issues → Labels). Job issues are tagged automatically when created.

### 2. Install the worker

```bash
./deploy/macos/install_worker.sh --node-id oyster-mini-solo
```

This installs a launchd agent that runs `watchtower worker run` at login and restarts on failure. Logs go to `/Volumes/omics/watchtower/logs/worker.log`.

To run without launchd (foreground debugging):

```bash
watchtower worker run --node-id oyster-mini-solo
```

### 3. How jobs enter the queue

| Source | What it does |
|--------|----------------|
| **GitHub Actions** | Daily scheduled discovery (`.github/workflows/discovery_schedule.yml`) creates `discover` issues; weekly report workflow handles digest housekeeping |
| **Manual discovery** | `watchtower discover --species crassostrea_gigas` on the Mac (creates issues when a token is configured) |
| **Downstream jobs** | Each completed step creates the next issue (download → analyze → report) |

On a single Mac mini, the same worker claims and runs every step in sequence (up to `max_concurrent_jobs` at once).

### 4. Smoke test

```bash
watchtower config validate
watchtower discover --species crassostrea_gigas
watchtower status
watchtower worker run --node-id oyster-mini-solo --once
```

If `discover` logs a 429 warning, it will retry automatically. Re-run after a minute if retries are exhausted.

### 5. Tuning for one machine

- **Disk:** Keep at least 200 GB free on `data_root`. Downloads and Nextflow workdirs grow quickly.
- **Concurrency:** Leave `max_concurrent_jobs: 1` until analyze jobs complete reliably; analysis is CPU- and memory-heavy.
- **NCBI rate limits:** Export `NCBI_API_KEY` in your shell profile (see below) before running discovery-heavy workloads.
- **Updates:** `cd /opt/watchtower/app && git pull` — config and code come from git; the worker picks up changes on restart.

## Multi-Node Deployment

### Independent fleet (full pipeline per machine)

**Recommended when Mac minis are in different physical locations** and cannot share a drive.

Each machine runs the complete pipeline on its own SSD or external volume. Every node uses the same four `job_types` as the single-node setup (`discover`, `download`, `analyze`, `report`), but with a **unique** `node_id` and its own `data_root`:

```yaml
# config/nodes/oyster-mini-lab-a.yaml (repeat per site with a new node_id)
node_id: oyster-mini-lab-a
hostname: lab-a-mac.local
data_root: /Volumes/omics/watchtower   # local to this Mac — not shared with other sites
capabilities:
  job_types:
    - discover
    - download
    - analyze
    - report
  max_concurrent_jobs: 1
  storage_gb_free_min: 200
  preferred_species:
    - crassostrea_gigas
profiles:
  - mac_arm64
```

On each Mac mini, repeat the one-time setup (clone, bootstrap, token, Salmon index), create a site-specific node config, commit it to git, then:

```bash
./deploy/macos/install_worker.sh --node-id oyster-mini-lab-a
```

**How coordination works**

- GitHub Issues remain the authoritative queue. Workers on every site poll the same issue list and claim jobs via labels.
- SQLite (`{data_root}/watchtower.db`) is a **per-node local cache** — each Mac has its own database file.
- Download and analyze jobs pass **absolute filesystem paths** (samplesheet and FASTQ locations under that node's `data_root`). Raw data never moves between sites automatically.
- A dataset's discover → download → analyze → report chain should complete on **one** machine. The worker that runs a download creates the analyze issue with paths on its own disk; the same node normally claims that follow-on job on the next poll.

**Partitioning work across sites**

To reduce the chance that site B claims an analyze job whose data lives on site A's disk:

- Give each site a distinct `preferred_species` when you expand to multiple species (Phase 2), or
- Run discovery from one place only (scheduled GitHub Action or a designated node) and let workers compete for download/analyze jobs, keeping `max_concurrent_jobs: 1` so the completing node tends to pick up the next step first.

If an analyze job is claimed by the wrong node, it will fail (missing files). Use `watchtower retry <job_id>` after fixing routing, or run `watchtower worker housekeeping` to release stale claims.

**Scaling goal:** more Mac minis processing **different** datasets in parallel, each with a self-contained copy of staged data and results — not splitting one dataset's pipeline across distant machines.

### Role-split cluster (shared storage required)

Use this only when **all Mac minis are colocated** and mount the **same** data volume at the same `data_root` path (shared Thunderbolt drive, NAS, etc.).

| Node | Config | Suggested role |
|------|--------|----------------|
| oyster-mini-01 | `config/nodes/oyster-mini-01.yaml` | discover, download |
| oyster-mini-02 | `config/nodes/oyster-mini-02.yaml` | analyze, report |

Install one worker per machine:

```bash
# On first Mac mini
./deploy/macos/install_worker.sh --node-id oyster-mini-01

# On second Mac mini
./deploy/macos/install_worker.sh --node-id oyster-mini-02
```

The download node writes FASTQ files and a samplesheet under the shared `data_root`. The analyze node reads those paths directly — this only works if both machines see the same files.

Each node pulls config from git and claims jobs matching its `capabilities.job_types`. GitHub Issues remain the authoritative queue; SQLite on each node is a local cache.

## NCBI API Key (recommended)

Discovery queries NCBI Entrez (SRA + GEO). Without an API key, NCBI allows about 3 requests per second per IP; the smoke-test `discover` command makes several calls in quick succession and may hit a temporary 429 if other tools are using the same IP.

Create a key at [NCBI account settings](https://www.ncbi.nlm.nih.gov/account/settings/), then add to your shell profile:

```bash
export NCBI_API_KEY="your_key_here"
```

With a key, you can raise `discovery.entrez_rate_limit_per_sec` to `10` in `config/watchtower.yaml`.

For launchd workers, add `NCBI_API_KEY` to the `EnvironmentVariables` dict in `~/Library/LaunchAgents/com.uw.watchtower.worker.plist` (or source it from a wrapper script), then `launchctl unload` / `launchctl load` the plist.

## Maintenance

- Update code: `cd /opt/watchtower/app && git pull`
- Reclaim stale jobs: `watchtower worker housekeeping --node-id <node-id>`
- Check logs: `tail -f /Volumes/omics/watchtower/logs/worker.log`
- Worker status: `launchctl list | grep watchtower`

## Uninstall

To completely remove watchtower from a Mac mini, use the uninstall script. It reverses everything `bootstrap.sh` and `install_worker.sh` set up: the launchd worker service, the conda `watchtower` environment, the editable pip package, the Nextflow binary, and the app directory.

```bash
cd /opt/watchtower/app

# Preview what would be removed (changes nothing)
./deploy/macos/uninstall.sh --dry-run

# Interactive uninstall — keeps the data root
./deploy/macos/uninstall.sh

# Non-interactive uninstall — keeps the data root
./deploy/macos/uninstall.sh --yes

# Also delete the data root (raw downloads, runs, reports, logs, DBs)
./deploy/macos/uninstall.sh --purge-data
```

**Data is preserved by default.** The data root (`/Volumes/omics/watchtower`) is only deleted when you pass `--purge-data`, and even then the script asks for confirmation unless combined with `--yes`.

The defaults can be overridden with environment variables if you installed to non-standard locations:

```bash
APP_DIR=/opt/watchtower/app \
DATA_ROOT=/Volumes/omics/watchtower \
ENV_NAME=watchtower \
./deploy/macos/uninstall.sh
```

### What the script does not remove

These are shared tools the script leaves in place — remove them manually only if nothing else on the machine depends on them:

- **Homebrew** and the `git` / `jq` formulae installed by `bootstrap.sh` (`brew uninstall jq`)
- **mambaforge** itself (`rm -rf "$HOME/mambaforge"`) — only the `watchtower` conda environment is removed, not the conda installation
- The `NCBI_API_KEY` export you may have added to your shell profile

### Manual uninstall (if you prefer to do it by hand)

```bash
# 1. Stop and remove the worker service
launchctl unload ~/Library/LaunchAgents/com.uw.watchtower.worker.plist
rm -f ~/Library/LaunchAgents/com.uw.watchtower.worker.plist

# 2. Remove the conda environment
mamba env remove -n watchtower --yes

# 3. Remove the Nextflow binary and cache
sudo rm -f /usr/local/bin/nextflow
rm -rf ~/.nextflow

# 4. Remove the app directory
sudo rm -rf /opt/watchtower/app

# 5. (Optional) Remove the data root — DELETES ALL DOWNLOADED DATA
rm -rf /Volumes/omics/watchtower
```
