# Operations Guide

For initial Mac mini setup (single machine or fleet), see [deploy/docs/node_setup.md](../deploy/docs/node_setup.md).

## Daily Operations

```bash
watchtower status                    # Local DB summary
watchtower worker run --node-id ID   # Start worker (or use launchd)
watchtower discover                  # Manual discovery run
watchtower report --weekly           # Generate weekly digest
```

## Job Lifecycle

1. **Discovery** — searches SRA/GEO, scores datasets, creates download issues
2. **Download** — fetches FASTQ, writes samplesheet, creates analyze issue
3. **Analyze** — runs Nextflow pipeline, creates report issue
4. **Report** — syncs artifacts to reports branch

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Worker idle, never picks up jobs | Confirm capacity: a job left `running` after a crash blocks the slot. Restarting the worker now auto-clears orphaned local jobs on startup; also run `watchtower worker housekeeping --node-id ID` to release stale GitHub claims. |
| Worker appears frozen mid-job | A download or Nextflow run is hung. Each external tool has a wall-clock timeout (see README); lower the relevant `WATCHTOWER_*_TIMEOUT` to fail faster, or check the network / pipeline. |
| `ImportError` / commands behave oddly | You are almost certainly on the wrong Python. Run `python --version` — it must be 3.11 from the `watchtower` conda env, not base Anaconda 3.8. |
| `pip install -e` fails with "requires a setup.py" | Old pip/setuptools in a base env. Use the `watchtower` conda env (Python 3.11) and a recent pip. |
| Jobs stuck in running | `watchtower worker housekeeping --node-id ID` |
| Download failures | Check sra-tools, disk space, accession validity |
| Nextflow failures | Check Salmon index path in reference manifest |
| Config errors | `watchtower config validate` |

## Retry Failed Jobs

```bash
watchtower retry <job_id>
```

## Secrets

- `GITHUB_TOKEN` — Keychain via `watchtower github store-token`
- `NCBI_API_KEY` — optional, export in worker environment
