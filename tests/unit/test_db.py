"""Database layer tests."""

import json
from pathlib import Path

import pytest

from watchtower.db.connection import connect
from watchtower.db.models import Artifact, Dataset, Job, JobEvent, Node, PipelineRun, Sample
from watchtower.db.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    conn = connect(tmp_path / "test.db")
    return Store(conn)


def test_upsert_and_get_dataset(store: Store) -> None:
    ds = Dataset(
        dataset_id="sra:SRR123",
        source="sra",
        accession="SRR123",
        title="Test study",
        taxonomy_id=29159,
        relevance_score=75.0,
        status="scored",
    )
    store.upsert_dataset(ds)
    loaded = store.get_dataset("sra:SRR123")
    assert loaded is not None
    assert loaded.accession == "SRR123"
    assert loaded.relevance_score == 75.0


def test_upsert_sample(store: Store) -> None:
    store.upsert_dataset(
        Dataset(dataset_id="sra:SRR123", source="sra", accession="SRR123")
    )
    store.upsert_sample(
        Sample(sample_id="SRR123_1", dataset_id="sra:SRR123", condition="control")
    )
    samples = store.list_samples("sra:SRR123")
    assert len(samples) == 1
    assert samples[0].condition == "control"


def test_job_lifecycle(store: Store) -> None:
    job = Job(job_id="job1", job_type="download", status="queued")
    store.upsert_job(job)
    store.add_job_event(JobEvent(job_id="job1", event_type="claimed", message="n1"))
    loaded = store.get_job("job1")
    assert loaded is not None
    assert loaded.status == "queued"
    events = store.list_job_events("job1")
    assert len(events) == 1


def test_pipeline_run_and_artifacts(store: Store) -> None:
    store.upsert_job(Job(job_id="j1", job_type="analyze"))
    run = PipelineRun(run_id="r1", job_id="j1", status="succeeded")
    store.upsert_pipeline_run(run)
    store.add_artifact(
        Artifact(artifact_id="a1", run_id="r1", artifact_type="deg_table", path="/tmp/deg.csv")
    )
    artifacts = store.list_artifacts("r1")
    assert len(artifacts) == 1


def test_node_heartbeat(store: Store) -> None:
    store.upsert_node(
        Node(node_id="mini-01", hostname="mini.local", capabilities_json=json.dumps({}))
    )
    node = store.get_node("mini-01")
    assert node is not None
    assert node.node_id == "mini-01"


def test_list_datasets_by_status(store: Store) -> None:
    store.upsert_dataset(
        Dataset(
            dataset_id="sra:A", source="sra", accession="A",
            status="queued", relevance_score=80,
        )
    )
    store.upsert_dataset(
        Dataset(
            dataset_id="sra:B", source="sra", accession="B",
            status="skipped", relevance_score=10,
        )
    )
    queued = store.list_datasets(status="queued")
    assert len(queued) == 1
    assert queued[0].accession == "A"
