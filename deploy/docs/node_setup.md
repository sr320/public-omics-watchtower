# Mac Mini Node Setup

You can run public-omics-watchtower on **one Mac mini** (full pipeline) or split work across **multiple Mac minis** (discovery/download vs analysis/report). Start with a single node unless you need to scale out.

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

Split roles when you want discovery/downloads on one Mac and analysis/reports on another (or when a single machine runs out of disk or CPU).

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
