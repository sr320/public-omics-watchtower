# Configuration

Configuration is layered YAML under `config/`.

## Layers

1. `config/watchtower.yaml` — global settings
2. `config/species/*.yaml` — per-species taxonomy, keywords, references
3. `config/repositories/*.yaml` — SRA/GEO Entrez queries
4. `config/scoring/relevance.yaml` — relevance scoring weights
5. `config/pipelines/*.yaml` — Nextflow pipeline parameters
6. `config/nodes/*.yaml` — per-node capabilities (no secrets)

## Validation

```bash
watchtower config validate
```

## Adding a Species (Phase 2)

1. Create `config/species/<species_id>.yaml`
2. Add to `enabled_species` in `watchtower.yaml`
3. Add reference manifest under `references/<species_id>/`
4. Create `species:<species_id>` GitHub label
