"""Configuration validation tests."""

from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError

from watchtower.config.loader import load_watchtower_config
from watchtower.config.validator import (
    parse_issue_frontmatter,
    validate_issue_body,
    validate_watchtower_config,
)


def test_load_watchtower_config() -> None:
    cfg = load_watchtower_config()
    assert cfg["github"]["repo"] == "public-omics-watchtower"
    assert "crassostrea_gigas" in cfg["enabled_species"]


def test_validate_all_configs() -> None:
    configs = validate_watchtower_config()
    assert "species" in configs
    assert "crassostrea_gigas" in configs["species"]


def test_validate_issue_body() -> None:
    fixture = Path("tests/fixtures/mock_issue_body.yaml")
    data = yaml.safe_load(fixture.read_text())
    validate_issue_body(data)


def test_parse_issue_frontmatter() -> None:
    body = """---
job_id: test:discover
job_type: discover
species: crassostrea_gigas
schema_version: 1
---
## Context
Test job
"""
    data = parse_issue_frontmatter(body)
    assert data["job_id"] == "test:discover"
    assert data["job_type"] == "discover"


def test_invalid_issue_body_raises() -> None:
    with pytest.raises(JsonSchemaValidationError):
        validate_issue_body({"job_type": "invalid"})
