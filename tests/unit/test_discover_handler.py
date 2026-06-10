"""Discovery handler tests."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from watchtower.db.connection import connect
from watchtower.db.store import Store
from watchtower.queue.models import QueueJob
from watchtower.worker.handlers.discover import handle_discover


class MockEntrez:
    def esearch(self, db: str, term: str, retmax: int = 100) -> list[str]:
        return []

    def esummary(self, db: str, ids: list[str]) -> list[dict]:
        return []


@pytest.fixture
def store(tmp_path: Path) -> Store:
    conn = connect(tmp_path / "test.db")
    return Store(conn)


def test_handle_discover_records_job_event(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "watchtower.worker.handlers.discover.EntrezClient.from_config",
        lambda: MockEntrez(),
    )
    queue = MagicMock()
    job = QueueJob(
        job_id="discover:crassostrea_gigas:manual",
        job_type="discover",
        species="crassostrea_gigas",
        payload={"species": ["crassostrea_gigas"]},
        created_by="cli@watchtower",
    )

    handle_discover(job, store, queue)

    saved = store.get_job(job.job_id)
    assert saved is not None
    assert saved.status == "succeeded"
    events = store.list_job_events(job.job_id)
    assert len(events) == 1
    assert events[0].event_type == "discover_complete"
