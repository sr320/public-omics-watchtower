"""YAML configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from watchtower.utils.paths import find_repo_root


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def config_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "config"


def load_watchtower_config(repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "watchtower.yaml")


def load_species_config(species_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "species" / f"{species_id}.yaml")


def load_repository_config(source: str, repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "repositories" / f"{source}.yaml")


def load_scoring_config(repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "scoring" / "relevance.yaml")


def load_pipeline_config(pipeline_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "pipelines" / f"{pipeline_id}.yaml")


def load_node_config(node_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "nodes" / f"{node_id}.yaml")


def load_ai_config(name: str, repo_root: Path | None = None) -> dict[str, Any]:
    return load_yaml(config_dir(repo_root) / "ai" / f"{name}.yaml")


def load_all_configs(repo_root: Path | None = None) -> dict[str, Any]:
    """Load and compose all configuration layers."""
    root = repo_root or find_repo_root()
    wt = load_watchtower_config(root)
    species: dict[str, Any] = {}
    for species_id in wt.get("enabled_species", []):
        species[species_id] = load_species_config(species_id, root)

    return {
        "watchtower": wt,
        "species": species,
        "repositories": {
            "sra": load_repository_config("sra", root),
            "geo": load_repository_config("geo", root),
        },
        "scoring": load_scoring_config(root),
        "pipelines": {
            "rnaseq_salmon_deseq2": load_pipeline_config("rnaseq_salmon_deseq2", root),
        },
        "ai": {
            "prioritizer": load_ai_config("prioritizer", root),
            "reporter": load_ai_config("reporter", root),
        },
    }
