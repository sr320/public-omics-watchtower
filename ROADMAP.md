# Roadmap

This document describes the phased delivery plan for **public-omics-watchtower**, from the current Phase 1 vertical slice through cross-study meta-analysis and AI-assisted interpretation.

---

## Vision

Build an autonomous, reproducible, configuration-driven platform that:

1. Discovers new public omics datasets
2. Prioritizes datasets by scientific relevance to marine stress biology
3. Downloads and stages selected datasets
4. Executes reproducible bioinformatics workflows
5. Generates differential expression results and biological summaries
6. Produces weekly reports for the laboratory
7. Scales across multiple Apple Silicon Mac mini worker nodes
8. Uses GitHub as the central control plane

**Primary research focus:** University of Washington marine genomics — oysters, clams, mussels, corals, echinoderms, fish, environmental stress biology, epigenetics, and aquaculture resilience.

---

## Phase 1 — Pacific Oyster RNA-seq (Current)

**Status:** Implemented

### Scope

| Dimension | Phase 1 |
|-----------|---------|
| Species | *Crassostrea gigas* (Pacific oyster) |
| Data type | RNA-seq |
| Repositories | NCBI SRA, NCBI GEO |
| Pipeline | Salmon → DESeq2 |
| Outputs | DEG tables, PCA plots, volcano plots, GO enrichment, Markdown reports, weekly digests |

### Delivered Capabilities

- [x] YAML-driven configuration with schema validation
- [x] SRA and GEO discovery via Entrez E-utilities
- [x] Relevance scoring for marine stress biology keywords
- [x] GitHub Issues as distributed work queue
- [x] SQLite per-node cache and run manifests
- [x] Worker daemon with `discover → download → analyze → report` handlers
- [x] SRA download and sample sheet staging
- [x] Nextflow RNA-seq pipeline with `mac_arm64` profile
- [x] Per-study and weekly Markdown reports
- [x] Multi-node support with stale claim recovery
- [x] GitHub Actions for CI, scheduled discovery, and weekly reports
- [x] AI extension point stubs (`NullPrioritizer`, `NullInterpreter`)
- [x] Mac mini deployment scripts (bootstrap, launchd)

### Phase 1 Exit Criteria

- [ ] Salmon index built for C. gigas reference transcriptome
- [ ] End-to-end unattended run on a new public dataset
- [ ] Weekly digest generated and published to `reports` branch
- [ ] Two Mac minis processing jobs without duplicate execution

### Open Decisions (Resolve Before Production)

1. **C. gigas reference transcriptome** — lab-curated vs NCBI GCF (affects Salmon index and GO annotation)
2. **Data volume strategy** — internal storage vs external Thunderbolt drives per node
3. **GitHub token model** — fine-grained PAT per node vs GitHub App (App preferred for production)

---

## Phase 2 — Multi-Species Expansion

**Status:** Planned

**Target:** Extend discovery, scoring, and analysis to additional marine and aquaculture species without changing the job model or queue protocol.

### Species Targets

| Species | Scientific Name | Priority |
|---------|-----------------|----------|
| Olympia oyster | *Ostrea lurida* | High |
| Manila clam | *Ruditapes philippinarum* | High |
| Mussels | *Mytilus* spp. | High |
| Sunflower sea star | *Pycnopodia helianthoides* | Medium |
| Corals | Multiple genera | Medium |

### Planned Work

| Work Item | Description |
|-----------|-------------|
| Species configs | Add `config/species/{species_id}.yaml` per species |
| Reference manifests | Add `references/{species_id}/manifest.yaml` and Salmon index docs |
| Label routing | Use `species:{species_id}` GitHub labels for job routing |
| Stress keyword tuning | Per-species stress vocabulary in scoring config |
| GO annotation | Species-specific or ortholog-based gene annotation for enrichment |
| Node routing | Assign species to nodes via `preferred_species` in node config |
| Phase 2 docs | Expand `docs/phase2_species.md` with per-species setup guides |

### Data Types (Phase 2 Consideration)

Phase 2 focuses on RNA-seq (same pipeline). Future data types (WGBS, ATAC-seq, proteomics) are out of scope until Phase 3 planning.

### AI Integration (Phase 2)

| Feature | Provider | Config |
|---------|----------|--------|
| Dataset prioritization | `watchtower.ai.prioritizer` | `config/ai/prioritizer.yaml` |
| Report biological summaries | `watchtower.ai.interpreter` | `config/ai/reporter.yaml` |

Enable by setting `provider` and `enabled: true` in AI config files. Phase 1 stubs remain the default.

### Phase 2 Exit Criteria

- At least three additional species configured and enabled
- Discovery returns relevant datasets for each enabled species
- Per-species Salmon indices documented and buildable
- Jobs route correctly by `species:*` labels across the node fleet

---

## Phase 3 — Cross-Study Meta-Analysis

**Status:** Planned

**Target:** Aggregate results across completed studies to identify recurring stress-response genes, pathways, and candidate biomarkers.

### Planned Capabilities

| Capability | Description |
|------------|-------------|
| Recurring DE genes | Genes differentially expressed across multiple stress studies |
| Recurring pathways | GO/pathway terms enriched in multiple independent datasets |
| Stress-response atlas | Consolidated view of stress biology across species and conditions |
| Biomarker ranking | Ranked candidate biomarkers from cross-study evidence |
| Meta-analysis reports | Weekly digest section: "recurring stress genes" |

### Planned Components

| Component | Location |
|-----------|----------|
| New job type | `job:metaanalyze` |
| Database tables | `gene_occurrences`, `pathway_occurrences`, `biomarker_candidates` |
| Aggregator | `watchtower/meta/` or `pipelines/meta/` |
| AI consumer | `InterpreterProvider.suggest_biomarkers()` |

### Meta-Analysis Workflow (Conceptual)

```
completed DEG tables (all studies)
        │
        ▼
  normalize gene IDs (species orthologs)
        │
        ▼
  frequency analysis (gene × study matrix)
        │
        ▼
  pathway aggregation (GO / KEGG)
        │
        ▼
  biomarker ranking (AI-assisted in Phase 3)
        │
        ▼
  stress-response atlas report
```

### Phase 3 Exit Criteria

- Meta-analysis job runs across ≥10 completed C. gigas studies
- Recurring gene and pathway tables published to `reports/meta/`
- Weekly digest includes cross-study summary section
- Biomarker candidates ranked with provenance links to source studies

---

## Timeline Overview

```
2026 Q2   Phase 1 complete — C. gigas vertical slice in production
2026 Q3   Phase 2 begin — O. lurida, R. philippinarum, Mytilus
2026 Q4   Phase 2 complete — P. helianthoides, corals; AI prioritization enabled
2027 Q1   Phase 3 begin — cross-study meta-analysis infrastructure
2027 Q2   Phase 3 complete — stress-response atlas and biomarker ranking
```

Timelines are approximate and depend on reference genome availability, lab priorities, and Mac mini fleet capacity.

---

## Non-Goals (All Phases)

- Kubernetes or cloud-native orchestration
- Paid SaaS services (managed workflow engines, cloud compute)
- Private/clinical data (platform is designed for public SRA/GEO only)
- Real-time streaming analysis
- Web UI (GitHub Issues + CLI + Markdown reports are the interface)

---

## How to Contribute to the Roadmap

1. **Phase 1 production hardening** — reference data, end-to-end validation, ops runbooks
2. **Phase 2 species** — add `config/species/`, reference manifests, and stress keyword sets
3. **Phase 3 meta** — design `gene_occurrences` schema and cross-study normalization strategy
4. **AI providers** — implement `PrioritizerProvider` and `InterpreterProvider` backends

See [MILESTONES.md](MILESTONES.md) for the completed Phase 1 development breakdown and [ARCHITECTURE.md](ARCHITECTURE.md) for system design details.
