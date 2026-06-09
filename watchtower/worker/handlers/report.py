"""Report job handler — sync artifacts and finalize study report."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from watchtower.config.loader import load_watchtower_config
from watchtower.db.models import JobEvent
from watchtower.db.store import Store
from watchtower.queue.models import QueueJob
from watchtower.utils.logging import get_logger
from watchtower.utils.paths import find_repo_root
from watchtower.worker.node import NodeManager

logger = get_logger(__name__)


def handle_report(
    job: QueueJob,
    store: Store,
    node: NodeManager,
) -> Path | None:
    """Sync report artifacts to reports directory."""
    run_id = job.payload.get("run_id", "")
    outdir = Path(job.payload.get("outdir", ""))
    wt = load_watchtower_config()
    repo_root = find_repo_root()

    reports_local = node.data_root / "reports" / "studies" / run_id
    reports_local.mkdir(parents=True, exist_ok=True)

    if outdir.exists():
        for sub in ("deg", "plots", "enrichment", "report"):
            src = outdir / sub
            if src.exists():
                dest = reports_local / sub
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)

    report_md = reports_local / "report" / "study_report.md"
    if not report_md.exists() and outdir.exists():
        alt = outdir / "report" / "study_report.md"
        if alt.exists():
            report_md.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(alt, report_md)

    store.add_job_event(
        JobEvent(
            job_id=job.job_id,
            event_type="report_complete",
            message=f"Report staged at {reports_local}",
        )
    )

    _maybe_push_reports(repo_root, reports_local, wt, run_id)
    logger.info("Report handler complete for run %s", run_id)
    return report_md if report_md.exists() else None


def _maybe_push_reports(
    repo_root: Path,
    reports_local: Path,
    wt_config: dict,
    run_id: str,
) -> None:
    """Push reports to reports branch if git and token available."""
    reports_branch = wt_config.get("github", {}).get("reports_branch", "reports")
    github_cfg = wt_config.get("github", {})
    owner = github_cfg.get("owner", "")
    repo = github_cfg.get("repo", "")

    import os

    if not os.environ.get("GITHUB_TOKEN"):
        logger.debug("Skipping reports branch push: no GITHUB_TOKEN")
        return

    target = repo_root / ".reports_sync" / run_id
    target.mkdir(parents=True, exist_ok=True)
    for item in reports_local.rglob("*"):
        if item.is_file():
            rel = item.relative_to(reports_local)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    sync_script = repo_root / "watchtower" / "reporting" / "sync_reports.py"
    if sync_script.exists():
        subprocess.run(
            [
                "python", str(sync_script),
                "--owner", owner,
                "--repo", repo,
                "--branch", reports_branch,
                "--source", str(target),
                "--prefix", f"studies/{run_id}",
            ],
            check=False,
            capture_output=True,
        )
