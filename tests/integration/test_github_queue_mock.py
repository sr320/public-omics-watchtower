"""GitHub queue integration tests with mocked API."""

from unittest.mock import MagicMock, patch

from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.queue.models import QueueJob


def test_create_job_payload() -> None:
    q = GitHubIssuesQueue(owner="test", repo="watchtower", token="fake")
    job = QueueJob(
        job_id="SRR1:download:rnaseq_v1",
        job_type="download",
        species="crassostrea_gigas",
        dataset_id="sra:SRR1",
        priority=70,
        payload={"accession": "SRR1", "source": "sra"},
    )
    body = q.format_issue_body(job, "Test context")
    assert "job_id:" in body
    assert "SRR1:download" in body


@patch.object(GitHubIssuesQueue, "_request")
def test_claim_job_success(mock_request: MagicMock) -> None:
    queue = GitHubIssuesQueue(owner="test", repo="watchtower", token="fake")
    mock_request.side_effect = [
        {"labels": [{"name": "job:download"}, {"name": "status:queued"}]},
        None,
        None,
    ]
    result = queue.claim_job(1, "oyster-mini-01", "job1")
    assert result is True
    assert mock_request.call_count == 3


@patch.object(GitHubIssuesQueue, "get_issue_labels")
def test_claim_job_already_claimed(mock_labels: MagicMock) -> None:
    queue = GitHubIssuesQueue(owner="test", repo="watchtower", token="fake")
    mock_labels.return_value = ["status:running", "claimed-by:oyster-mini-02"]
    result = queue.claim_job(1, "oyster-mini-01", "job1")
    assert result is False
