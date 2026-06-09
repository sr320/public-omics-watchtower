#!/usr/bin/env python3
"""Render study markdown report from pipeline outputs."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path


def count_significant_deg(deg_path: Path) -> tuple[int, int]:
    total = 0
    sig = 0
    with deg_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            total += 1
            try:
                padj = float(row.get("padj", "") or "nan")
                lfc = float(row.get("log2FoldChange", "") or "0")
                if padj < 0.05 and abs(lfc) >= 1.0:
                    sig += 1
            except ValueError:
                continue
    return total, sig


def top_genes(deg_path: Path, n: int = 20) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with deg_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)

    def sort_key(r: dict[str, str]) -> float:
        try:
            return float(r.get("padj", "1") or "1")
        except ValueError:
            return 1.0

    rows.sort(key=sort_key)
    return rows[:n]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deg", required=True, type=Path)
    parser.add_argument("--pca", required=True, type=Path)
    parser.add_argument("--volcano", required=True, type=Path)
    parser.add_argument("--go", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--contrast", default="treatment_vs_control")
    args = parser.parse_args()

    total, sig = count_significant_deg(args.deg)
    top = top_genes(args.deg)

    lines = [
        "# Study Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Contrast:** {args.contrast}",
        "",
        "## Summary",
        f"- Total genes tested: {total}",
        f"- Significant DEGs (padj < 0.05, |LFC| >= 1): {sig}",
        "",
        "## Figures",
        f"- PCA: `{args.pca.name}`",
        f"- Volcano: `{args.volcano.name}`",
        "",
        "## Top Differentially Expressed Genes",
        "",
        "| gene_id | log2FoldChange | padj |",
        "| --- | --- | --- |",
    ]

    for row in top:
        gid = row.get("gene_id", "")
        lfc = row.get("log2FoldChange", "")
        padj = row.get("padj", "")
        lines.append(f"| {gid} | {lfc} | {padj} |")

    lines.extend([
        "",
        "## GO Enrichment",
        f"Results: `{args.go.name}`",
        "",
        "## Reproducibility",
        "- Pipeline: watchtower-rnaseq v1.0.0",
        "- Quantification: Salmon",
        "- Differential expression: DESeq2",
        "",
        "## AI Summary",
        "_AI interpretation not enabled in Phase 1._",
        "",
    ])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
