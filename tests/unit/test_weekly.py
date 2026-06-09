"""Weekly report tests."""

from pathlib import Path

from watchtower.db.connection import connect
from watchtower.db.models import Dataset, Job, PipelineRun
from watchtower.db.store import Store
from watchtower.reporting.weekly import generate_weekly_digest, week_bounds


def test_week_bounds() -> None:
    report_id, start, end = week_bounds()
    assert "-W" in report_id
    assert len(start) == 10


def test_generate_weekly_digest(tmp_path: Path) -> None:
    store = Store(connect(tmp_path / "t.db"))
    store.upsert_dataset(
        Dataset(
            dataset_id="sra:SRR1",
            source="sra",
            accession="SRR1",
            title="Test",
            status="queued",
            relevance_score=70,
        )
    )
    store.upsert_job(
        Job(
            job_id="j1",
            job_type="analyze",
            dataset_id="sra:SRR1",
            status="succeeded",
            finished_at="2099-01-01",
        )
    )
    store.upsert_pipeline_run(
        PipelineRun(run_id="r1", job_id="j1", status="succeeded")
    )
    path = generate_weekly_digest(store, tmp_path / "reports", since="2000-01-01")
    assert path.exists()
    content = path.read_text()
    assert "Weekly Watchtower Digest" in content
