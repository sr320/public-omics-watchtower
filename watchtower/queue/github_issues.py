"""GitHub Issues work queue client."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import requests
import yaml

from watchtower.config.validator import parse_issue_frontmatter, validate_issue_body
from watchtower.queue.models import QueueJob, job_type_label, priority_label, status_label
from watchtower.utils.github_auth import resolve_github_token
from watchtower.utils.logging import get_logger

logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubQueueError(Exception):
    """GitHub queue operation failed."""


class GitHubIssuesQueue:
    """Distributed job queue backed by GitHub Issues."""

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str | None = None,
        priority_thresholds: dict[str, int] | None = None,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.token = token or resolve_github_token()
        self.priority_thresholds = priority_thresholds or {
            "high": 75,
            "normal": 50,
            "low": 0,
        }
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["X-GitHub-Api-Version"] = "2022-11-28"

    def _url(self, path: str) -> str:
        return f"{GITHUB_API}/repos/{self.owner}/{self.repo}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> Any:
        url = self._url(path)
        for attempt in range(retries):
            response = self.session.request(
                method, url, params=params, json=json_body, timeout=60
            )
            if response.status_code == 403 and "rate limit" in response.text.lower():
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                raise GitHubQueueError(
                    f"GitHub API {method} {path} failed: {response.status_code} {response.text}"
                )
            if response.status_code == 204:
                return None
            return response.json()
        raise GitHubQueueError(f"GitHub API exhausted retries for {method} {path}")

    def format_issue_body(self, job: QueueJob, context_md: str = "") -> str:
        frontmatter = yaml.safe_dump(job.to_frontmatter(), sort_keys=False).strip()
        body = f"---\n{frontmatter}---\n"
        if context_md:
            body += f"\n## Job context\n{context_md}\n"
        return body

    def build_labels(self, job: QueueJob) -> list[str]:
        labels = [
            job_type_label(job.job_type),
            status_label(job.status),
            f"species:{job.species}",
            priority_label(job.priority, self.priority_thresholds),
        ]
        if job.claimed_by:
            labels.append(f"claimed-by:{job.claimed_by}")
        return labels

    def create_job(self, job: QueueJob, context_md: str = "") -> int:
        if not self.token:
            raise GitHubQueueError(
                "GitHub token not configured. Run `watchtower github store-token` "
                "or export GITHUB_TOKEN."
            )
        validate_issue_body(job.to_frontmatter())
        payload = {
            "title": f"[{job.job_type}] {job.job_id}",
            "body": self.format_issue_body(job, context_md),
            "labels": self.build_labels(job),
        }
        issue = self._request("POST", "/issues", json_body=payload)
        issue_number = int(issue["number"])
        job.github_issue_number = issue_number
        logger.info("Created issue #%s for job %s", issue_number, job.job_id)
        return issue_number

    def list_open_jobs(
        self,
        job_type: str | None = None,
        status: str = "queued",
        species: str | None = None,
    ) -> list[QueueJob]:
        labels = [status_label(status)]
        if job_type:
            labels.append(job_type_label(job_type))
        if species:
            labels.append(f"species:{species}")

        issues = self._request(
            "GET",
            "/issues",
            params={"state": "open", "labels": ",".join(labels), "per_page": 100},
        )
        jobs: list[QueueJob] = []
        for issue in issues:
            if "pull_request" in issue:
                continue
            try:
                data = parse_issue_frontmatter(issue["body"])
                validate_issue_body(data)
                label_names = [lbl["name"] for lbl in issue.get("labels", [])]
                jobs.append(
                    QueueJob.from_frontmatter(
                        data,
                        issue_number=int(issue["number"]),
                        labels=label_names,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping invalid issue #%s: %s", issue["number"], exc)
        return jobs

    def get_issue_labels(self, issue_number: int) -> list[str]:
        issue = self._request("GET", f"/issues/{issue_number}")
        return [lbl["name"] for lbl in issue.get("labels", [])]

    def set_labels(self, issue_number: int, labels: list[str]) -> None:
        self._request(
            "PUT",
            f"/issues/{issue_number}/labels",
            json_body={"labels": labels},
        )

    def add_comment(self, issue_number: int, body: str) -> None:
        self._request(
            "POST",
            f"/issues/{issue_number}/comments",
            json_body={"body": body},
        )

    def claim_job(self, issue_number: int, node_id: str, job_id: str) -> bool:
        """Attempt atomic claim. Returns True if claim succeeded."""
        current_labels = self.get_issue_labels(issue_number)
        for label in current_labels:
            if label.startswith("claimed-by:"):
                logger.debug("Issue #%s already claimed by %s", issue_number, label)
                return False
            if label == "status:running":
                return False

        new_labels = [
            lbl
            for lbl in current_labels
            if lbl not in {"status:queued", "status:completed", "status:failed"}
        ]
        new_labels.append("status:running")
        new_labels.append(f"claimed-by:{node_id}")

        try:
            self.set_labels(issue_number, new_labels)
        except GitHubQueueError:
            return False

        timestamp = datetime.now(timezone.utc).isoformat()
        self.add_comment(
            issue_number,
            f"Claimed by `{node_id}` at {timestamp}\n\n```json\n"
            f"{json.dumps({'job_id': job_id, 'node_id': node_id, 'claimed_at': timestamp})}\n```",
        )
        logger.info("Claimed issue #%s for node %s", issue_number, node_id)
        return True

    def complete_job(self, issue_number: int, node_id: str, message: str = "") -> None:
        labels = self.get_issue_labels(issue_number)
        new_labels = [
            lbl
            for lbl in labels
            if not lbl.startswith("claimed-by:") and not lbl.startswith("status:")
        ]
        new_labels.extend(["status:completed", f"claimed-by:{node_id}"])
        self.set_labels(issue_number, new_labels)
        self.add_comment(issue_number, f"Completed by `{node_id}`.\n\n{message}")

    def fail_job(
        self,
        issue_number: int,
        node_id: str,
        error: str,
        needs_human: bool = False,
    ) -> None:
        labels = self.get_issue_labels(issue_number)
        new_labels = [
            lbl
            for lbl in labels
            if not lbl.startswith("status:")
        ]
        new_labels.append("status:failed")
        if needs_human:
            new_labels.append("needs:human")
        self.set_labels(issue_number, new_labels)
        self.add_comment(
            issue_number,
            f"Failed on `{node_id}`.\n\n```\n{error}\n```",
        )

    def release_stale_claims(self, stale_hours: int = 24) -> list[int]:
        """Reclaim issues stuck in running state. Returns reclaimed issue numbers."""
        issues = self._request(
            "GET",
            "/issues",
            params={"state": "open", "labels": "status:running", "per_page": 100},
        )
        reclaimed: list[int] = []
        cutoff = datetime.now(timezone.utc).timestamp() - stale_hours * 3600

        for issue in issues:
            if "pull_request" in issue:
                continue
            updated = datetime.fromisoformat(
                issue["updated_at"].replace("Z", "+00:00")
            ).timestamp()
            if updated > cutoff:
                continue

            issue_number = int(issue["number"])
            labels = [lbl["name"] for lbl in issue.get("labels", [])]
            new_labels = [
                lbl
                for lbl in labels
                if not lbl.startswith("claimed-by:") and not lbl.startswith("status:")
            ]
            new_labels.append("status:queued")
            self.set_labels(issue_number, new_labels)
            self.add_comment(
                issue_number,
                f"Stale claim released after {stale_hours}h inactivity.",
            )
            reclaimed.append(issue_number)
            logger.info("Reclaimed stale issue #%s", issue_number)

        return reclaimed

    def sync_jobs_to_store(self, store: Any, species: str | None = None) -> int:
        """Pull open queued/running issues into SQLite cache."""
        from watchtower.db.models import Job

        count = 0
        for status in ("queued", "running"):
            for qjob in self.list_open_jobs(status=status, species=species):
                store.upsert_job(
                    Job(
                        job_id=qjob.job_id,
                        job_type=qjob.job_type,
                        dataset_id=qjob.dataset_id,
                        status="running" if status == "running" else "queued",
                        claimed_by_node=qjob.claimed_by,
                        github_issue_number=str(qjob.github_issue_number),
                        payload_json=json.dumps(qjob.payload),
                    )
                )
                count += 1
        return count
