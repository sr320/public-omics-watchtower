# Mac Mini Node Setup

## Prerequisites

- Apple Silicon Mac mini (macOS 13+)
- External data volume mounted at `/Volumes/omics/watchtower`
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

# Store GitHub token in Keychain
watchtower github store-token

# Build Salmon index (see references/crassostrea_gigas/README.md)

# Install worker for this node
./deploy/macos/install_worker.sh --node-id oyster-mini-01
```

## Multi-Node Deployment

| Node | Config | Suggested role |
|------|--------|----------------|
| oyster-mini-01 | `config/nodes/oyster-mini-01.yaml` | discover, download |
| oyster-mini-02 | `config/nodes/oyster-mini-02.yaml` | analyze, report |

Each node pulls config from git and claims jobs matching its `capabilities.job_types`.

## NCBI API Key (recommended)

Discovery queries NCBI Entrez (SRA + GEO). Without an API key, NCBI allows about 3 requests per second per IP; the smoke-test `discover` command makes several calls in quick succession and may hit a temporary 429 if other tools are using the same IP.

Create a key at [NCBI account settings](https://www.ncbi.nlm.nih.gov/account/settings/), then add to your shell profile:

```bash
export NCBI_API_KEY="your_key_here"
```

With a key, you can raise `discovery.entrez_rate_limit_per_sec` to `10` in `config/watchtower.yaml`.

## Smoke Test

```bash
watchtower config validate
watchtower discover --species crassostrea_gigas
watchtower status
watchtower worker run --node-id oyster-mini-01 --once
```

If `discover` logs a 429 warning, it will retry automatically. Re-run after a minute if retries are exhausted.

## Maintenance

- Update code: `cd /opt/watchtower/app && git pull`
- Reclaim stale jobs: `watchtower worker housekeeping --node-id oyster-mini-01`
- Check logs: `tail -f /Volumes/omics/watchtower/logs/worker.log`
