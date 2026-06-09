"""Plot utilities (supplementary to Nextflow pipeline)."""

from __future__ import annotations

from pathlib import Path


def list_plot_artifacts(results_dir: Path) -> dict[str, list[Path]]:
    """Discover plot files in pipeline results directory."""
    plots: dict[str, list[Path]] = {"pca": [], "volcano": [], "other": []}
    plot_dir = results_dir / "plots"
    if not plot_dir.exists():
        return plots
    for p in plot_dir.glob("*.png"):
        name = p.name.lower()
        if "pca" in name:
            plots["pca"].append(p)
        elif "volcano" in name:
            plots["volcano"].append(p)
        else:
            plots["other"].append(p)
    return plots
