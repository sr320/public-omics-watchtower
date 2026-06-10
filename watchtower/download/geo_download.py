"""GEO-linked SRA download helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from watchtower.discovery.entrez import EntrezClient
from watchtower.download.sra import download_sra_accession
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)

SRA_ACCESSION_PATTERNS = (
    r"(SRR\d+)",
    r"(SRX\d+)",
    r"(SRS\d+)",
)
SRA_RUN_ACCESSION_PATTERN = re.compile(r'Run acc="(SRR\d+)"')


def extract_sra_accessions(geo_accession: str, metadata_text: str = "") -> list[str]:
    """Extract SRA run accessions from GEO metadata text."""
    found: set[str] = set()
    for pattern in SRA_ACCESSION_PATTERNS:
        found.update(re.findall(pattern, metadata_text))
    if not found and geo_accession.startswith("GSE"):
        logger.debug("No SRA accessions found in GEO %s metadata text", geo_accession)
    return sorted(found)


def parse_sra_run_accessions_from_summary(runs_field: str) -> list[str]:
    """Parse SRR accessions from an SRA esummary runs XML fragment."""
    return SRA_RUN_ACCESSION_PATTERN.findall(runs_field or "")


def fetch_sra_accessions_for_geo(
    geo_accession: str,
    entrez: EntrezClient | None = None,
) -> list[str]:
    """Resolve linked SRA run accessions for a GEO series via Entrez."""
    client = entrez or EntrezClient.from_config()
    gds_ids = client.esearch("gds", f"{geo_accession} AND gse[entry_type]", retmax=1)
    if not gds_ids:
        logger.warning("No GDS record found for GEO %s", geo_accession)
        return []

    sra_uids = client.elink("gds", "sra", gds_ids)
    if not sra_uids:
        logger.warning("No linked SRA records for GEO %s", geo_accession)
        return []

    accessions: set[str] = set()
    for summary in client.esummary("sra", sra_uids):
        runs = str(summary.get("runs", ""))
        accessions.update(parse_sra_run_accessions_from_summary(runs))
        if not runs:
            accessions.update(re.findall(r"(SRR\d+)", str(summary.get("expxml", ""))))

    resolved = sorted(accessions)
    logger.info("Resolved %d SRA runs for GEO %s", len(resolved), geo_accession)
    return resolved


def download_geo_dataset(
    data_root: Path,
    geo_accession: str,
    sra_accessions: list[str] | None = None,
    metadata_text: str = "",
    entrez: EntrezClient | None = None,
) -> tuple[Path, list[dict[str, Any]]]:
    """Download GEO dataset via linked SRA accessions."""
    accessions = sra_accessions or extract_sra_accessions(geo_accession, metadata_text)
    if not accessions:
        accessions = fetch_sra_accessions_for_geo(geo_accession, entrez=entrez)
    if not accessions:
        raise ValueError(f"No SRA accessions for GEO {geo_accession}")

    all_samples: list[dict[str, Any]] = []
    sheet_path: Path | None = None
    for sra_acc in accessions:
        sheet, samples = download_sra_accession(data_root, sra_acc)
        sheet_path = sheet
        for s in samples:
            s["geo_accession"] = geo_accession
            s["sra_accession"] = sra_acc
        all_samples.extend(samples)

    if sheet_path is None:
        raise ValueError("Download produced no samples")

    from watchtower.download.staging import write_sample_sheet

    geo_sheet = sheet_path.parent.parent / f"{geo_accession}_samplesheet.csv"
    write_sample_sheet(geo_sheet, all_samples)
    return geo_sheet, all_samples
