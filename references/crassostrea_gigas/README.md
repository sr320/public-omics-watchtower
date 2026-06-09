# Crassostrea gigas Reference Data

## Salmon Index

Build a Salmon index from the Pacific oyster reference transcriptome:

```bash
# Download RefSeq transcripts (example)
mkdir -p /Volumes/omics/watchtower/references/crassostrea_gigas/transcripts
# Place transcript FASTA at transcripts/transcripts.fa

salmon index \
  -t /Volumes/omics/watchtower/references/crassostrea_gigas/transcripts/transcripts.fa \
  -i /Volumes/omics/watchtower/references/crassostrea_gigas/salmon_index \
  --gencode
```

Update `salmon_index_path` in `manifest.yaml` if using a different location.

## Genome Reference

- **Accession:** GCF_000297895.1
- **Source:** [NCBI RefSeq](https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/297/895/GCF_000297895.1_ASM29789v2/)

## Notes

Phase 1 uses transcript-level quantification with Salmon. GO enrichment
requires a C. gigas gene-to-GO mapping; until available, enrichment outputs
list significant genes with `pending_annotation` placeholders.
