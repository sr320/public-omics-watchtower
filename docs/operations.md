# Operations Guide

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
