"""Queue job models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueueJob:
    job_id: str
    job_type: str
    species: str
    dataset_id: str | None = None
    priority: int = 50
    payload: dict[str, Any] = field(default_factory=dict)
    created_by: str = "watchtower"
    schema_version: int = 1
    github_issue_number: int | None = None
    labels: list[str] = field(default_factory=list)
    status: str = "queued"
    claimed_by: str | None = None

    def to_frontmatter(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "dataset_id": self.dataset_id,
            "species": self.species,
            "priority": self.priority,
            "payload": self.payload,
            "created_by": self.created_by,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_frontmatter(
        cls,
        data: dict[str, Any],
        issue_number: int | None = None,
        labels: list[str] | None = None,
    ) -> QueueJob:
        status = "queued"
        claimed_by = None
        label_list = labels or []
        for label in label_list:
            if label.startswith("claimed-by:"):
                claimed_by = label.split(":", 1)[1]
            if label == "status:running":
                status = "running"
            elif label == "status:completed":
                status = "succeeded"
            elif label == "status:failed":
                status = "failed"
            elif label == "status:queued":
                status = "queued"

        return cls(
            job_id=data["job_id"],
            job_type=data["job_type"],
            species=data["species"],
            dataset_id=data.get("dataset_id"),
            priority=int(data.get("priority", 50)),
            payload=data.get("payload", {}),
            created_by=data.get("created_by", "watchtower"),
            schema_version=int(data.get("schema_version", 1)),
            github_issue_number=issue_number,
            labels=label_list,
            status=status,
            claimed_by=claimed_by,
        )


def priority_label(score: int, thresholds: dict[str, int]) -> str:
    if score >= thresholds.get("high", 75):
        return "priority:high"
    if score >= thresholds.get("normal", 50):
        return "priority:normal"
    return "priority:low"


def job_type_label(job_type: str) -> str:
    return f"job:{job_type}"


def status_label(status: str) -> str:
    mapping = {
        "queued": "status:queued",
        "claimed": "status:running",
        "running": "status:running",
        "succeeded": "status:completed",
        "failed": "status:failed",
        "cancelled": "status:failed",
    }
    return mapping.get(status, "status:queued")
