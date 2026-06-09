"""GEO-linked SRA download helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from watchtower.download.sra import download_sra_accession
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)


def extract_sra_accessions(geo_accession: str, metadata_text: str = "") -> list[str]:
    """Extract SRA run accessions from GEO metadata text."""
    patterns = [
        r"(SRR\d+)",
        r"(SRX\d+)",
        r"(SRS\d+)",
    ]
    found: set[str] = set()
    for pattern in patterns:
        found.update(re.findall(pattern, metadata_text))
    if not found and geo_accession.startswith("GSE"):
        logger.warning("No SRA accessions found in GEO %s metadata", geo_accession)
    return sorted(found)


def download_geo_dataset(
    data_root: Path,
    geo_accession: str,
    sra_accessions: list[str] | None = None,
    metadata_text: str = "",
) -> tuple[Path, list[dict[str, Any]]]:
    """Download GEO dataset via linked SRA accessions."""
    accessions = sra_accessions or extract_sra_accessions(geo_accession, metadata_text)
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
