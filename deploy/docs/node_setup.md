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

## Smoke Test

```bash
watchtower config validate
watchtower discover --species crassostrea_gigas
watchtower status
watchtower worker run --node-id oyster-mini-01 --once
```

## Maintenance

- Update code: `cd /opt/watchtower/app && git pull`
- Reclaim stale jobs: `watchtower worker housekeeping --node-id oyster-mini-01`
- Check logs: `tail -f /Volumes/omics/watchtower/logs/worker.log`
