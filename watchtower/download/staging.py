"""Data staging layout and sample sheet generation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from watchtower.utils.paths import resolve_data_path


def raw_dir(data_root: Path, source: str, accession: str) -> Path:
    return resolve_data_path(data_root, "raw", source, accession)


def runs_dir(data_root: Path, run_id: str) -> Path:
    return resolve_data_path(data_root, "runs", run_id)


def write_sample_sheet(
    output_path: Path,
    samples: list[dict[str, Any]],
) -> Path:
    """Write Nextflow-compatible samplesheet CSV."""
    fieldnames = ["sample_id", "fastq_1", "fastq_2", "condition"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for sample in samples:
            writer.writerow({k: sample.get(k, "") for k in fieldnames})
    return output_path


def write_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    path = run_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def infer_condition(sample_name: str) -> str:
    """Heuristic condition assignment from sample name."""
    name_lower = sample_name.lower()
    if any(k in name_lower for k in ("control", "ctrl", "mock", "baseline")):
        return "control"
    if any(k in name_lower for k in ("stress", "treat", "exposed", "challenged")):
        return "treatment"
    return "unknown"
