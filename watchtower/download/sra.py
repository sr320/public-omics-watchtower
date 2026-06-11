"""SRA download utilities."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from watchtower.download.staging import infer_condition, raw_dir, write_sample_sheet
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)

# Wall-clock ceilings so a hung external tool can never freeze the worker forever.
# Override via environment for unusually large datasets.
PREFETCH_TIMEOUT_SEC = int(os.environ.get("WATCHTOWER_PREFETCH_TIMEOUT", 6 * 3600))
FASTERQ_TIMEOUT_SEC = int(os.environ.get("WATCHTOWER_FASTERQ_TIMEOUT", 6 * 3600))


class DownloadError(Exception):
    """Download operation failed."""


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(cmd: list[str], *, timeout: int, what: str) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with a timeout, converting hangs into DownloadError."""
    logger.info("Running (timeout %ds): %s", timeout, " ".join(cmd))
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise DownloadError(
            f"{what} timed out after {timeout}s. Increase the relevant "
            f"WATCHTOWER_*_TIMEOUT env var if this dataset is unusually large."
        ) from exc


def prefetch(accession: str, output_dir: Path, timeout: int = PREFETCH_TIMEOUT_SEC) -> Path:
    """Run prefetch for SRA accession."""
    prefetch_bin = _which("prefetch")
    if not prefetch_bin:
        raise DownloadError("prefetch not found in PATH; install sra-tools")

    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [prefetch_bin, accession, "-O", str(output_dir)]
    result = _run(cmd, timeout=timeout, what="prefetch")
    if result.returncode != 0:
        raise DownloadError(f"prefetch failed: {result.stderr}")

    sra_files = list(output_dir.rglob("*.sra"))
    if not sra_files:
        raise DownloadError(f"No .sra file found for {accession}")
    return sra_files[0]


def fasterq_dump(
    sra_path: Path,
    output_dir: Path,
    threads: int = 4,
    timeout: int = FASTERQ_TIMEOUT_SEC,
) -> list[Path]:
    """Convert SRA to FASTQ."""
    fasterq = _which("fasterq-dump")
    if not fasterq:
        raise DownloadError("fasterq-dump not found in PATH")

    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        fasterq,
        str(sra_path),
        "-O", str(output_dir),
        "-e", str(threads),
        "--split-files",
    ]
    result = _run(cmd, timeout=timeout, what="fasterq-dump")
    if result.returncode != 0:
        raise DownloadError(f"fasterq-dump failed: {result.stderr}")

    fastqs = sorted(output_dir.glob("*.fastq*"))
    if not fastqs:
        raise DownloadError(f"No FASTQ files produced from {sra_path}")
    return fastqs


def group_fastq_pairs(fastq_files: list[Path]) -> list[dict[str, Any]]:
    """Pair R1/R2 FASTQ files by sample prefix."""
    samples: dict[str, dict[str, Any]] = {}
    for fq in fastq_files:
        name = fq.name
        if "_1.fastq" in name or "_1.fq" in name:
            sample_id = name.split("_1")[0]
            samples.setdefault(sample_id, {"sample_id": sample_id})["fastq_1"] = str(fq)
        elif "_2.fastq" in name or "_2.fq" in name:
            sample_id = name.split("_2")[0]
            samples.setdefault(sample_id, {"sample_id": sample_id})["fastq_2"] = str(fq)
        else:
            sample_id = fq.stem
            samples.setdefault(sample_id, {"sample_id": sample_id})["fastq_1"] = str(fq)

    result = []
    for sample_id, data in samples.items():
        data["condition"] = infer_condition(sample_id)
        result.append(data)
    return result


def download_sra_accession(
    data_root: Path,
    accession: str,
    threads: int = 4,
) -> tuple[Path, list[dict[str, Any]]]:
    """Download and stage SRA accession; return sample sheet path and rows."""
    out_dir = raw_dir(data_root, "sra", accession)
    sra_path = prefetch(accession, out_dir)
    fastqs = fasterq_dump(sra_path, out_dir / "fastq", threads=threads)
    samples = group_fastq_pairs(fastqs)
    sheet_path = out_dir / "samplesheet.csv"
    write_sample_sheet(sheet_path, samples)
    return sheet_path, samples
