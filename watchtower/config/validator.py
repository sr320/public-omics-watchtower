"""Configuration and issue body validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from watchtower.config.loader import load_all_configs, load_yaml
from watchtower.utils.paths import find_repo_root


class ValidationError(Exception):
    """Raised when configuration validation fails."""


def schema_path(name: str, repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / "schemas" / name


def load_json_schema(name: str, repo_root: Path | None = None) -> dict[str, Any]:
    path = schema_path(name, repo_root)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_issue_body(data: dict[str, Any], repo_root: Path | None = None) -> None:
    schema = load_json_schema("issue_body.schema.json", repo_root)
    jsonschema.validate(instance=data, schema=schema)


def validate_watchtower_config(repo_root: Path | None = None) -> dict[str, Any]:
    """Validate all configuration files load and required keys exist."""
    root = repo_root or find_repo_root()
    errors: list[str] = []

    try:
        configs = load_all_configs(root)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(f"Failed to load configs: {exc}") from exc

    wt = configs["watchtower"]
    required_wt = ["github", "discovery", "queue", "enabled_species"]
    for key in required_wt:
        if key not in wt:
            errors.append(f"watchtower.yaml missing key: {key}")

    for species_id in wt.get("enabled_species", []):
        sp = configs["species"].get(species_id)
        if not sp:
            errors.append(f"Missing species config: {species_id}")
            continue
        for key in ("taxonomy_id", "scientific_name", "stress_keywords"):
            if key not in sp:
                errors.append(f"species/{species_id}.yaml missing key: {key}")

    for node_file in (root / "config" / "nodes").glob("*.yaml"):
        if node_file.name.startswith("_"):
            continue
        node = load_yaml(node_file)
        for key in ("node_id", "data_root", "capabilities"):
            if key not in node:
                errors.append(f"{node_file.name} missing key: {key}")

    if errors:
        raise ValidationError("; ".join(errors))

    return configs


def parse_issue_frontmatter(body: str) -> dict[str, Any]:
    """Parse YAML frontmatter from GitHub issue body."""
    if not body.startswith("---"):
        raise ValidationError("Issue body must start with YAML frontmatter")
    parts = body.split("---", 2)
    if len(parts) < 3:
        raise ValidationError("Invalid frontmatter block")
    import yaml

    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise ValidationError("Frontmatter must be a mapping")
    return data
