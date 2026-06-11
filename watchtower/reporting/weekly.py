"""Weekly digest report generation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from watchtower.config.loader import load_watchtower_config
from watchtower.db.connection import connect
from watchtower.db.models import ReportItem, WeeklyReport
from watchtower.db.store import Store
from watchtower.queue.github_issues import GitHubIssuesQueue
from watchtower.utils.paths import find_repo_root


def week_bounds(reference: datetime | None = None) -> tuple[str, str, str]:
    """Return (report_id, week_start, week_end) for ISO week."""
    ref = reference or datetime.now(timezone.utc)
    week_start = ref - timedelta(days=7)
    # isocalendar() returns a plain tuple on Python 3.8 and a named tuple on
    # 3.9+; index access works on both.
    iso = ref.isocalendar()
    report_id = f"{iso[0]}-W{iso[1]:02d}"
    return (
        report_id,
        week_start.strftime("%Y-%m-%d"),
        ref.strftime("%Y-%m-%d"),
    )


def generate_weekly_digest(
    store: Store,
    output_dir: Path,
    since: str | None = None,
) -> Path:
    """Generate weekly markdown digest from completed studies."""
    repo_root = find_repo_root()
    templates_dir = repo_root / "templates" / "reports"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    template = env.get_template("weekly_digest.md.j2")

    report_id, week_start, week_end = week_bounds()
    if since is None:
        since = week_start

    completed = store.list_completed_reports_since(since)
    new_datasets = store.list_datasets(status="queued", limit=50)
    failed_jobs = store.list_jobs(status="failed", limit=20)

    context = {
        "report_id": report_id,
        "week_start": week_start,
        "week_end": week_end,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "completed_studies": completed,
        "new_datasets": [
            {
                "accession": d.accession,
                "title": d.title,
                "score": d.relevance_score,
                "source": d.source,
            }
            for d in new_datasets
        ],
        "failed_jobs": [
            {"job_id": j.job_id, "type": j.job_type, "error": j.error_message}
            for j in failed_jobs
        ],
        "study_count": len(completed),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "weekly" / f"{report_id}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.render(**context), encoding="utf-8")

    store.upsert_weekly_report(
        WeeklyReport(
            report_id=report_id,
            week_start=week_start,
            week_end=week_end,
            path=str(output_path),
            status="completed",
        )
    )
    for study in completed:
        store.add_report_item(
            ReportItem(
                report_id=report_id,
                dataset_id=study.get("dataset_id"),
                run_id=study.get("run_id"),
                summary_json=json.dumps({
                    "accession": study.get("accession"),
                    "title": study.get("title"),
                    "score": study.get("relevance_score"),
                }),
            )
        )

    return output_path


def publish_weekly_issue(queue: GitHubIssuesQueue, digest_path: Path) -> int:
    """Open GitHub Issue with weekly digest summary."""
    from watchtower.queue.models import QueueJob

    report_id = digest_path.stem
    body_preview = digest_path.read_text(encoding="utf-8")[:4000]
    job = QueueJob(
        job_id=f"weekly:{report_id}",
        job_type="report",
        species="crassostrea_gigas",
        priority=50,
        payload={"report_path": str(digest_path), "report_id": report_id},
        created_by="weekly@watchtower",
    )
    return queue.create_job(
        job,
        context_md=f"## Weekly Watchtower Digest\n\n{body_preview}",
    )


def run_weekly_report(data_root: Path | None = None) -> Path:
    """CLI entrypoint for weekly report generation."""
    wt = load_watchtower_config()
    root = find_repo_root()
    dr = data_root or Path(wt.get("paths", {}).get("data_root", root / "data"))
    conn = connect(dr / "watchtower.db")
    store = Store(conn)
    output = generate_weekly_digest(store, dr / "reports")
    return output
