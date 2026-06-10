"""Queue model tests."""

import yaml

from watchtower.queue.models import QueueJob, job_type_label, priority_label, status_label


def test_queue_job_frontmatter() -> None:
    job = QueueJob(
        job_id="test:download",
        job_type="download",
        species="crassostrea_gigas",
        dataset_id="sra:SRR1",
        priority=82,
        payload={"accession": "SRR1"},
    )
    fm = job.to_frontmatter()
    assert fm["job_id"] == "test:download"
    assert fm["payload"]["accession"] == "SRR1"


def test_discover_job_frontmatter_omits_dataset_id() -> None:
    from watchtower.config.validator import validate_issue_body

    job = QueueJob(
        job_id="discover:crassostrea_gigas:manual",
        job_type="discover",
        species="crassostrea_gigas",
        payload={"species": ["crassostrea_gigas"]},
        created_by="cli@watchtower",
    )
    fm = job.to_frontmatter()
    assert "dataset_id" not in fm
    validate_issue_body(fm)


def test_queue_job_from_frontmatter() -> None:
    data = yaml.safe_load(open("tests/fixtures/mock_issue_body.yaml"))
    job = QueueJob.from_frontmatter(
        data,
        issue_number=42,
        labels=["job:download", "status:queued", "species:crassostrea_gigas"],
    )
    assert job.github_issue_number == 42
    assert job.status == "queued"


def test_labels() -> None:
    assert job_type_label("analyze") == "job:analyze"
    assert status_label("succeeded") == "status:completed"
    assert priority_label(80, {"high": 75, "normal": 50}) == "priority:high"
